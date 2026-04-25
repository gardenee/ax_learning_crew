"""식당/메뉴 검색 서비스 — Qdrant vector search 기반.

세션 3 의 핵심 모듈. 에이전트 tool 과 분리해 서비스 계층에 둔다.

두 컬렉션:
- `restaurants` : 식당 수준 검색 — "회식하기 좋은 고깃집" 처럼 분위기/근거 중심
- `menus`       : 메뉴 수준 검색 — "뭐 먹지?" 같은 음식 결정 단계

흐름:
  1. query 문자열 → e5 모델로 임베딩 (1024-dim, `query: ` prefix)
  2. Qdrant 에서 top_k (또는 rerank 시 top_k*3) 조회
  3. filter (제외 keyword / 제외 restaurant_id / near geo_radius / 예산 / 평점) 적용
  4. (옵션) rerank_service 로 재정렬
  5. payload 를 dict 리스트로 반환
"""

from __future__ import annotations

import logging
import random
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
QUERY_PREFIX = "query: "
RESTAURANT_COLLECTION = "restaurants"
MENU_COLLECTION = "menus"

_embedder = None
_qdrant_client = None


def _get_embedder():
    """fastembed 모델을 lazy 로드한다."""
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedder = TextEmbedding(EMBEDDING_MODEL)
    return _embedder


def _get_qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
    return _qdrant_client


def embed_query(query: str) -> list[float]:
    """query 문자열을 벡터로 변환한다. e5 는 `query: ` prefix 필수."""
    model = _get_embedder()
    prefixed = QUERY_PREFIX + query
    return list(next(model.embed([prefixed])))


# ──────────────────────────────────────────────────────────────────────
# 내부 helper: filter / Qdrant fetch
# ──────────────────────────────────────────────────────────────────────

def _resolve_excluded_ids(filter_spec: dict[str, Any] | None) -> list[str]:
    """`filter.exclude_restaurant_ids` 만 그대로 반환한다."""
    if not filter_spec:
        return []
    return list(filter_spec.get("exclude_restaurant_ids") or [])


def _build_query_filter(
    filter_spec: dict[str, Any] | None,
    excluded_ids: list[str],
) -> qmodels.Filter | None:
    """must_not (제외 restaurant_id) + must (geo_radius) 를 조합한다."""
    must: list[qmodels.Condition] = []
    must_not: list[qmodels.Condition] = []

    if excluded_ids:
        must_not.append(
            qmodels.FieldCondition(
                key="restaurant_id",
                match=qmodels.MatchAny(any=excluded_ids),
            )
        )

    # exclude_keywords 가 태그/dish_types 에 걸린 식당 제외
    if filter_spec:
        kw_excl: list[str] = filter_spec.get("exclude_keywords") or []
        for kw in kw_excl:
            must_not.append(
                qmodels.FieldCondition(key="tags", match=qmodels.MatchValue(value=kw))
            )
            must_not.append(
                qmodels.FieldCondition(key="dish_types", match=qmodels.MatchValue(value=kw))
            )

        near = filter_spec.get("near") or None
        if near and near.get("lat") is not None and near.get("lng") is not None:
            # 도보 N분 제약은 1km=15분 기준 m 로 변환. radius_m 과 동시에 오면 분이 우선.
            max_walk_minutes = near.get("max_walk_minutes")
            if max_walk_minutes is not None:
                radius_m = float(max_walk_minutes) * 1000.0 / 15.0
            else:
                radius_m = float(near.get("radius_m") or 800)
            must.append(
                qmodels.FieldCondition(
                    key="location",
                    geo_radius=qmodels.GeoRadius(
                        center=qmodels.GeoPoint(
                            lat=float(near["lat"]), lon=float(near["lng"])
                        ),
                        radius=radius_m,
                    ),
                )
            )

    if not must and not must_not:
        return None
    return qmodels.Filter(must=must or None, must_not=must_not or None)


def _post_filter_restaurants(
    hits: list[dict[str, Any]], filter_spec: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Python 레벨 post-filter — 예산/평점 같은 숫자 조건."""
    if not filter_spec:
        return hits

    budget_max = filter_spec.get("budget_max")
    min_rating = filter_spec.get("min_rating")

    if budget_max is None and min_rating is None:
        return hits

    out = []
    for h in hits:
        if budget_max is not None:
            try:
                pm = float(h.get("price_max") or h.get("price_min") or 0)
                if pm and pm > float(budget_max):
                    continue
            except (TypeError, ValueError):
                pass

        if min_rating is not None:
            try:
                r = float(h.get("rating") or 0)
                if r < float(min_rating):
                    continue
            except (TypeError, ValueError):
                pass

        out.append(h)
    return out


# ──────────────────────────────────────────────────────────────────────
# 다양성 helper: multi-query RRF + tie-break 셔플
# ──────────────────────────────────────────────────────────────────────

RRF_K = 60  # Reciprocal Rank Fusion 상수. 60 은 원 논문 권장치.


def _rrf_merge(
    per_query_hits: list[list[dict[str, Any]]],
    id_key: str = "restaurant_id",
) -> list[dict[str, Any]]:
    """여러 쿼리의 검색 결과를 Reciprocal Rank Fusion 으로 합친다.

    각 쿼리 결과의 rank 만 써서 합치므로 쿼리 간 점수 스케일 차이에 강하다.
    같은 식당이 여러 쿼리에 등장하면 rank 기여분이 누적 → 자연스럽게 상위로.

    반환 hits 에는 원 벡터 점수 `score` (여러 쿼리 중 최댓값) 와 `rrf_score` 가
    함께 실린다. 이후 단계(post-filter, rerank) 는 `score` 를 그대로 쓰면 된다.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for hits in per_query_hits:
        for rank, h in enumerate(hits):
            rid = h.get(id_key)
            if not rid:
                continue
            contribution = 1.0 / (rank + RRF_K)
            existing = by_id.get(rid)
            if existing is None:
                new_hit = dict(h)
                new_hit["rrf_score"] = contribution
                by_id[rid] = new_hit
            else:
                existing["rrf_score"] += contribution
                if float(h.get("score") or 0.0) > float(existing.get("score") or 0.0):
                    existing["score"] = float(h["score"])

    merged = list(by_id.values())
    merged.sort(key=lambda x: x["rrf_score"], reverse=True)
    return merged


def _tie_break_shuffle(
    results: list[dict[str, Any]],
    score_key: str,
    randomness: float,
) -> list[dict[str, Any]]:
    """점수가 비슷한 인접 후보끼리 그룹으로 묶어 그룹 내부만 셔플한다.

    randomness ∈ [0,1] 에 비례해 ε (동점 판정 폭) 이 커진다. seed 없이 매번 랜덤.
    """
    if not results or randomness <= 0:
        return results

    r = max(0.0, min(1.0, float(randomness)))
    epsilon = 0.02 + 0.08 * r  # r=0 → 0.02, r=1 → 0.10

    rng = random.Random()  # seed 없음 = time-based 엔트로피

    out: list[dict[str, Any]] = []
    i = 0
    n = len(results)
    while i < n:
        leader = float(results[i].get(score_key) or 0.0)
        j = i + 1
        while j < n and abs(float(results[j].get(score_key) or 0.0) - leader) < epsilon:
            j += 1
        group = results[i:j]
        if len(group) > 1:
            rng.shuffle(group)
        out.extend(group)
        i = j
    return out


# ──────────────────────────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────────────────────────

def search_restaurants(
    query: str,
    top_k: int = 5,
    filter: dict[str, Any] | None = None,
    use_rerank: bool = False,
    rerank_weights: dict[str, float] | None = None,
    boost_concepts: list[str] | None = None,
    queries: list[str] | None = None,
    randomness: float = 0.0,
) -> list[dict[str, Any]]:
    """query 로 식당 top_k 개를 벡터 검색한다.

    Args:
        query: 자연어 검색어. `queries` 가 없을 때의 단일 쿼리.
        top_k: 최종 반환 수. use_rerank=True 면 top_k*3 을 fetch 한 뒤 rerank.
        filter: {
            "exclude_keywords":      [str], # memory.dislikes — 한국어 태그 매칭
            "exclude_restaurant_ids":[str], # 최근 식사 이력 place_id
            "near": {"lat": float, "lng": float, "max_walk_minutes": float, "radius_m": float},  # geo_radius 하드 필터 (분 우선)
            "budget_max":             int,  # 메뉴 최고 가격 상한
            "min_rating":           float,  # 평점 하한
        }
        use_rerank: True 면 vector search 결과를 rerank_service 로 재정렬.
        rerank_weights: rerank 가중치 override. 예 {"keyword": 1.0}.
        boost_concepts: memory.likes 같은 선호 concept — rerank 키워드 신호에 가산.
        queries: 2개 이상 넘기면 각 쿼리로 독립 검색한 뒤 Reciprocal Rank Fusion
            으로 합쳐 후보 풀을 키운다 (다양성 ↑). 비어있거나 None 이면 `query` 하나만 사용.
        randomness: 0.0~1.0. 0 이면 결정적. 높일수록 rerank_score(또는 vector score)
            가 유사한 인접 후보들끼리 그룹 셔플 (seed 없음 = 매번 신선). 권장 범위 0.2~0.4.

    반환: payload + score + (rerank 시) rerank_score/components 가 실린 dict 리스트.
    """
    client = _get_qdrant()

    excluded_ids = _resolve_excluded_ids(filter)
    query_filter = _build_query_filter(filter, excluded_ids)

    search_limit = top_k * 3 if use_rerank else top_k * 2  # post-filter 여유

    # 1) 단일 쿼리 or multi-query + RRF
    effective_queries = [q for q in (queries or []) if q] or [query]

    per_query_hits: list[list[dict[str, Any]]] = []
    for q in effective_queries:
        vector = embed_query(q)
        response = client.query_points(
            collection_name=RESTAURANT_COLLECTION,
            query=vector,
            limit=search_limit,
            with_payload=True,
            query_filter=query_filter,
        )
        hits: list[dict[str, Any]] = []
        for hit in response.points:
            payload = dict(hit.payload or {})
            payload["score"] = float(hit.score)
            hits.append(payload)
        per_query_hits.append(hits)

    if len(per_query_hits) > 1:
        results = _rrf_merge(per_query_hits, id_key="restaurant_id")
    else:
        results = per_query_hits[0]

    # 2) 후처리 필터 (예산/평점)
    results = _post_filter_restaurants(results, filter)

    # 3) Rerank — 원 쿼리(query) 기준으로 관련성 산출
    if use_rerank:
        from app.services.ranking.rerank_service import rerank

        results = rerank(
            query, results,
            weights=rerank_weights,
            boost_concepts=boost_concepts,
        )
        score_key = "rerank_score"
    else:
        score_key = "score"

    # 4) 유사 점수 그룹 셔플 (매번 신선)
    if randomness > 0:
        results = _tie_break_shuffle(results, score_key=score_key, randomness=randomness)

    return results[:top_k]


def search_menus(
    query: str,
    top_k: int = 5,
    filter: dict[str, Any] | None = None,
    use_rerank: bool = False,
    rerank_weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """query 로 메뉴를 검색하고 중복 메뉴명을 dedupe 해 "음식 종류" 를 반환한다.

    "오늘 뭐 먹지?" 처럼 음식 결정 단계에 쓴다.

    흐름:
      1. menus 컬렉션에서 top_k*5 개 벡터 검색
      2. exclude_keywords / exclude_restaurant_ids 로 걸러냄
      3. 메뉴명(name) 으로 dedupe — 같은 "칼국수" 가 여러 집에 있어도 1건으로 집계
         (각 메뉴에 available_at: 식당명 리스트 / sample_size 부착)
      4. (옵션) rerank
      5. 상위 top_k 반환

    반환 예:
      [
        {
          "menu_name": "칼국수",
          "score": 0.82,
          "available_at": ["YY칼국수", "AA분식"],
          "sample_size": 2,
          "example_description": "멸치 육수 기반 칼국수",
        }, ...
      ]
    """
    vector = embed_query(query)
    client = _get_qdrant()

    excluded_ids = _resolve_excluded_ids(filter)
    query_filter = _build_query_filter(filter, excluded_ids)

    fetch_limit = max(top_k * 5, 25)
    response = client.query_points(
        collection_name=MENU_COLLECTION,
        query=vector,
        limit=fetch_limit,
        with_payload=True,
        query_filter=query_filter,
    )

    # menus 컬렉션은 tags/dish_types payload 가 없어서 _build_query_filter 의
    # exclude_keywords 매칭이 안 걸린다. 메뉴 이름 substring 으로 직접 거른다.
    excluded_kw: list[str] = []
    if filter:
        excluded_kw = [str(k).strip() for k in (filter.get("exclude_keywords") or []) if str(k).strip()]

    # 같은 메뉴명 dedupe — 최고 점수 하나만 대표로, 나머지는 available_at 으로 집계
    by_name: dict[str, dict[str, Any]] = {}
    for hit in response.points:
        p = dict(hit.payload or {})
        name = (p.get("name") or "").strip()
        if not name:
            continue
        if excluded_kw and any(kw in name for kw in excluded_kw):
            continue
        score = float(hit.score)
        entry = by_name.get(name)
        if entry is None:
            by_name[name] = {
                "menu_name": name,
                "score": score,
                "available_at": [p.get("restaurant_name")] if p.get("restaurant_name") else [],
                "example_description": p.get("description"),
                "example_restaurant_id": p.get("restaurant_id"),
            }
        else:
            if p.get("restaurant_name") and p["restaurant_name"] not in entry["available_at"]:
                entry["available_at"].append(p["restaurant_name"])
            # 점수는 최고값 유지
            if score > entry["score"]:
                entry["score"] = score
                entry["example_description"] = p.get("description") or entry["example_description"]

    results = list(by_name.values())
    for r in results:
        r["sample_size"] = len(r["available_at"])

    if use_rerank:
        from app.services.ranking.rerank_service import rerank_menus

        results = rerank_menus(query, results, weights=rerank_weights)
    else:
        results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]
