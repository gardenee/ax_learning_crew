"""search_restaurants tool — 자연어 질의로 식당 검색.

벡터 검색/필터/rerank 로직은 `app.services.retrieval.search_service` 에 있고,
이 파일은 결과를 에이전트가 인용하기 좋은 형태로 포맷팅하는 얇은 어댑터다.

──────────────────────────────────────────────────────────────
크루원 수정 포인트가 많은 tool 입니다. `# [student-edit]` 여러 곳을 찾아보세요.
토글: `tool_search` — search_menus 와 함께 묶여 있습니다.
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


def _build_map_url(name: str | None, lat: float | None, lng: float | None) -> str | None:
    """식당 이름 + 좌표로 Kakao Map deep link 생성.

    좌표가 있으면 정확한 핀 링크, 없으면 이름 검색 URL 로 fallback.
    """
    if not name:
        return None
    name_q = quote(str(name), safe="")
    if lat is not None and lng is not None:
        return f"https://map.kakao.com/link/map/{name_q},{lat},{lng}"
    return f"https://map.kakao.com/?q={name_q}"


def handle(
    query: str,
    top_k: int = 5,
    filter: dict[str, Any] | None = None,
    use_rerank: bool = False,
    rerank_weights: dict[str, float] | None = None,
    boost_concepts: list[str] | None = None,
    queries: list[str] | None = None,
    randomness: float = 0.0,
) -> dict:
    """자연어 query 로 식당을 검색해 에이전트가 쓸 형태로 반환한다.

    Args:
        query: 사용자 맥락이 녹아있는 한 줄 자연어 검색어.
        top_k: 상위 몇 곳을 받을지 (기본 5).
        filter: {
            exclude_keywords, exclude_restaurant_ids, near, budget_max, min_rating
        } — memory 에서 뽑은 제약 + 근처 좌표 제약을 넘긴다.
        use_rerank: True 면 vector + keyword + popularity + memory 신호로 재정렬.
        rerank_weights: 신호별 가중치 override.
        boost_concepts: memory.likes 같은 선호 concept — rerank 단계에서 가산.

    반환 구조 (에이전트가 읽어 근거를 인용할 수 있는 필드 중심):
      {
        "query": <입력 그대로>,
        "candidates": [
           {
             "restaurant_id": ..., "name": ...,
             "score": ...,                      # vector 유사도
             "rerank_score": ..., "rerank_components": {...},  # use_rerank=True 일 때만
             "category": ..., "address": ...,
             "tags": [...], "dishes": [...],
             "rating": ...,
             "review_summary": ...,             # 근거 인용 원천
             "price_range": "9000~11000",
           }, ...
        ],
        "total": <개수>,
        "used_rerank": <bool>,
      }
    """
    from app.services.retrieval.search_service import search_restaurants as vector_search

    hits = vector_search(
        query=query,
        top_k=top_k,
        filter=filter,
        use_rerank=use_rerank,
        rerank_weights=rerank_weights,
        boost_concepts=boost_concepts,
        queries=queries,
        randomness=randomness,
    )

    candidates = []
    for hit in hits:
        price_min = hit.get("price_min")
        price_max = hit.get("price_max")
        price_range = None
        if price_min or price_max:
            price_range = f"{price_min or ''}~{price_max or ''}".strip("~") or None

        # [student-edit] 후보 dict 에 들어갈 필드를 선택하세요.
        # 이 필드들이 LLM 에게 보내질 context 가 됩니다.
        # 넣을수록 근거를 풍부하게 인용할 수 있지만 context 가 무거워집니다.
        # 예: review_summary 를 잘라 보낸다 / menus 필드를 추가한다 /
        #     opening_hours 를 넣는다 / 전화번호를 뺀다 등.
        entry = {
            "restaurant_id": hit.get("restaurant_id"),
            "name": hit.get("name"),
            "score": round(hit.get("score", 0.0), 4),
            "category": hit.get("primary_category"),
            "address": hit.get("short_address") or hit.get("address"),
            "lat": hit.get("lat"),
            "lng": hit.get("lng"),
            "tags": hit.get("tags", []),
            "dishes": hit.get("dish_types", []),
            "rating": hit.get("rating"),
            "review_summary": hit.get("review_summary"),
            "price_range": price_range,
            "map_url": _build_map_url(hit.get("name"), hit.get("lat"), hit.get("lng")),
        }
        if "rerank_score" in hit:
            # [student-edit] rerank 결과를 LLM 에게 어디까지 보여줄지 정하세요.
            # rerank_components 는 신호별 세부 점수가 들어있어 디버깅에 좋지만
            # LLM 이 점수에 과도 의존하게 될 수 있습니다.
            entry["rerank_score"] = hit["rerank_score"]
            entry["rerank_components"] = hit.get("rerank_components")
        candidates.append(entry)

    return {
        "query": query,
        "candidates": candidates,
        "total": len(candidates),
        "used_rerank": use_rerank,
    }
