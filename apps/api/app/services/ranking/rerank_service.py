"""교육용 rerank — 세션 3 rerank 실습 모듈.

이 모듈은 의도적으로 **규칙 기반** 으로 단순화한 교육용 rerank 다:
  restaurant rerank:
    α·vector + β·keyword_overlap + γ·popularity + δ·memory_boost

  menu rerank:
    α·vector + β·keyword_overlap + γ·menu_popularity
"""

from __future__ import annotations

import math
from typing import Any

DEFAULT_RESTAURANT_WEIGHTS = {
    "vector": 1.0,
    "keyword": 0.6,
    "popularity": 0.2,
    "memory": 0.4,
}

DEFAULT_MENU_WEIGHTS = {
    "vector": 1.0,
    "keyword": 0.6,
    "popularity": 0.3,
}


def _tokenize(text: str) -> set[str]:
    """아주 단순한 토크나이즈"""
    if not text:
        return set()
    raw = text.replace("|", " ").replace(",", " ").replace("·", " ")
    return {t for t in raw.split() if len(t) >= 2}


def _keyword_overlap(query: str, blob: str) -> float:
    """query 토큰과 blob 텍스트의 교집합 비율 (0~1)."""
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    h_tokens = _tokenize(blob)
    if not h_tokens:
        return 0.0
    inter = q_tokens & h_tokens
    return len(inter) / len(q_tokens)


def _restaurant_blob(hit: dict[str, Any]) -> str:
    return " ".join(
        [
            str(hit.get("name") or ""),
            str(hit.get("primary_category") or ""),
            " ".join(hit.get("tags") or []),
            " ".join(hit.get("dish_types") or []),
            str(hit.get("review_summary") or ""),
        ]
    )


def _popularity_restaurant(hit: dict[str, Any]) -> float:
    """rating + log(blog_hit_count) 를 0~1 근방으로 정규화."""
    rating = hit.get("rating")
    rating_component = 0.0
    if rating is not None:
        rating_component = max(0.0, (float(rating) - 3.0) / 2.0)  # 3.0 이하 = 0, 5.0 = 1.0

    hits = hit.get("blog_hit_count") or 0
    log_component = min(1.0, math.log1p(hits) / math.log1p(10000))
    return 0.5 * rating_component + 0.5 * log_component


def _memory_boost(hit: dict[str, Any], boost_concepts: list[str] | None) -> float:
    """memory.likes가 hit payload 에 얼마나 걸리는지.

    tags / dish_types / primary_category 를 문자열 blob 으로 만들어
    각 concept_key 가 대소문자 무시 부분일치하면 1점 — 최대 1.0 으로 정규화.

    더 강한 매칭을 원하면 concept_key → 한국어 라벨 매핑 테이블(`concepts.label_ko`) 을 조회하도록 확장하면 된다.
    """
    if not boost_concepts:
        return 0.0
    blob = " ".join(
        [
            str(hit.get("primary_category") or ""),
            " ".join(hit.get("tags") or []),
            " ".join(hit.get("dish_types") or []),
        ]
    ).lower()
    if not blob:
        return 0.0
    hits = sum(1 for k in boost_concepts if k and k.lower() in blob)
    return min(1.0, hits / max(1, len(boost_concepts)))


def rerank(
    query: str,
    hits: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
    boost_concepts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """식당 hits 를 규칙 기반 점수로 재정렬한다.

    각 hit 에 `rerank_score` / `rerank_components` 를 붙여 내림차순 정렬한 새 리스트를 반환한다.
    """
    w = {**DEFAULT_RESTAURANT_WEIGHTS, **(weights or {})}
    out: list[dict[str, Any]] = []
    for h in hits:
        vec = float(h.get("score", 0.0))
        kw = _keyword_overlap(query, _restaurant_blob(h))
        pop = _popularity_restaurant(h)
        mem = _memory_boost(h, boost_concepts)
        total = (
            w["vector"] * vec
            + w["keyword"] * kw
            + w["popularity"] * pop
            + w["memory"] * mem
        )

        item = dict(h)
        item["rerank_score"] = round(total, 4)
        item["rerank_components"] = {
            "vector": round(vec, 4),
            "keyword": round(kw, 4),
            "popularity": round(pop, 4),
            "memory": round(mem, 4),
        }
        out.append(item)

    out.sort(key=lambda x: x["rerank_score"], reverse=True)
    return out


def rerank_menus(
    query: str,
    hits: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """메뉴 hits 재정렬. 식당 rerank 와 공식은 비슷하지만 신호 재료가 다르다."""
    w = {**DEFAULT_MENU_WEIGHTS, **(weights or {})}
    out: list[dict[str, Any]] = []
    for h in hits:
        vec = float(h.get("score", 0.0))
        blob = " ".join(
            [
                str(h.get("menu_name") or ""),
                str(h.get("example_description") or ""),
            ]
        )
        kw = _keyword_overlap(query, blob)
        sample = int(h.get("sample_size") or 0)
        pop = min(1.0, math.log1p(sample) / math.log1p(10))
        total = w["vector"] * vec + w["keyword"] * kw + w["popularity"] * pop

        item = dict(h)
        item["rerank_score"] = round(total, 4)
        item["rerank_components"] = {
            "vector": round(vec, 4),
            "keyword": round(kw, 4),
            "popularity": round(pop, 4),
        }
        out.append(item)

    out.sort(key=lambda x: x["rerank_score"], reverse=True)
    return out
