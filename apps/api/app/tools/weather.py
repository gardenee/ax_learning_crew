"""get_weather tool — 실시간 날씨 조회.

Open-Meteo API (https://api.open-meteo.com/v1/forecast) 를 호출해 현재 날씨를
반환한다. 키 불필요, 공개 엔드포인트.
"""
from __future__ import annotations

import httpx


def wmo_to_condition(code: int) -> str:
    """WMO weather code → condition 문자열.

    버킷이 거칠지만 추천 로직엔 충분하다.
    """
    if code <= 3:
        return "clear"
    if code <= 48:
        return "cloudy"
    if 51 <= code <= 67:
        return "rain"
    if 71 <= code <= 77:
        return "snow"
    if 80 <= code <= 99:
        return "storm"
    return "cloudy"


_CONDITION_KR = {
    "clear":  "맑음",
    "cloudy": "흐림",
    "rain":   "비",
    "snow":   "눈",
    "storm":  "뇌우",
}


def handle(latitude: float, longitude: float) -> dict:
    resp = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code",
        },
        timeout=5.0,
    )
    resp.raise_for_status()
    cur = resp.json()["current"]
    condition = wmo_to_condition(int(cur["weather_code"]))
    temp = float(cur["temperature_2m"])
    return {
        "summary": f"{_CONDITION_KR.get(condition, condition)}, {temp:.0f}°C",
        "temperature_c": temp,
        "apparent_temperature_c": float(cur["apparent_temperature"]),
        "precipitation_mm": float(cur["precipitation"]),
        "condition": condition,
    }
