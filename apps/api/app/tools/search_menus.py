"""search_menus tool — 메뉴(음식 종류) 추천.

2단계 추천 플로우의 첫 단계:
  1) "뭐 먹지?"       → search_menus       → 메뉴 제안 (칼국수/국밥/...)
  2) "칼국수로 해줘"   → search_restaurants → 해당 메뉴를 파는 식당

Qdrant `menus` 컬렉션을 벡터 검색한 뒤 메뉴명으로 dedupe 해 "같은 칼국수가
10집에 있어도 1개 카드" 로 집계한다. 집계 과정에서 `available_at` (그 메뉴를
파는 식당 이름들) 이 자동으로 붙는다.

──────────────────────────────────────────────────────────────
완성본. `tool_search` 토글로 search.py 와 함께 묶여 있습니다.
구조가 search.py 와 거의 같으니 그쪽을 먼저 읽으면 이해가 빠릅니다.
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any


def handle(
    query: str,
    top_k: int = 5,
    filter: dict[str, Any] | None = None,
    use_rerank: bool = False,
    rerank_weights: dict[str, float] | None = None,
) -> dict:
    """자연어 query 로 "지금 상황에 맞는 음식(메뉴)" 을 추천한다.

    반환 구조:
      {
        "query": ...,
        "candidates": [
          {
            "menu_name": "칼국수",
            "score": ...,
            "rerank_score": ...,       # use_rerank=True 일 때
            "available_at": ["YY칼국수집", "AA분식"],
            "sample_size": 2,
            "example_description": "멸치 육수 기반 칼국수",
          }, ...
        ],
        "total": ...,
        "used_rerank": ...,
      }
    """
    from app.services.retrieval.search_service import search_menus as vector_search

    hits = vector_search(
        query=query,
        top_k=top_k,
        filter=filter,
        use_rerank=use_rerank,
        rerank_weights=rerank_weights,
    )

    candidates = []
    for hit in hits:
        entry = {
            "menu_name": hit.get("menu_name"),
            "score": round(hit.get("score", 0.0), 4),
            "available_at": hit.get("available_at", []),
            "sample_size": hit.get("sample_size", 0),
            "example_description": hit.get("example_description"),
        }
        if "rerank_score" in hit:
            entry["rerank_score"] = hit["rerank_score"]
            entry["rerank_components"] = hit.get("rerank_components")
        candidates.append(entry)

    return {
        "query": query,
        "candidates": candidates,
        "total": len(candidates),
        "used_rerank": use_rerank,
    }
