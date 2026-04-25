"""estimate_travel_time tool — 도보 이동시간 추정.

haversine 직선거리 + 평균 도보 속도로 계산한다. 외부 지도 API 를 붙이지 않는
대신 오차는 대략 ±30% 정도 — 추천 의사결정에는 충분하다.

입력 스키마:
    origin       = {"lat": float, "lng": float}
    destinations = [{"name": str, "lat": float, "lng": float}, ...]

반환 스키마:
    {"origin": {...},
     "candidates": [{"name", "distance_m", "walk_minutes", "source"}, ...]}

──────────────────────────────────────────────────────────────
완성본. `tool_travel` 토글로 껐다 켤 수 있습니다.
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import math

# [student-edit] 평균 도보 속도 (m/s). 한국은 대략 1.2~1.4 m/s.
# 값을 높이면 walk_minutes 가 작아져 후보가 "더 가까워" 보입니다.
# 신호등/인도 상태를 반영하려면 값을 조금 낮춰보세요.
WALK_MPS = 1.25


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 위경도 사이 직선거리 (m)."""
    R = 6_371_000.0  # 지구 반지름 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmd = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmd / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _estimate_single(origin: dict, dest: dict) -> dict:
    d = haversine_m(origin["lat"], origin["lng"], dest["lat"], dest["lng"])
    return {
        "name": dest.get("name", ""),
        "distance_m": round(d),
        "walk_minutes": round(d / WALK_MPS / 60, 1),
        "source": "haversine",
    }


def handle(origin: dict, destinations: list[dict]) -> dict:
    results = [_estimate_single(origin, d) for d in destinations]
    return {
        "origin": origin,
        "candidates": results,
    }
