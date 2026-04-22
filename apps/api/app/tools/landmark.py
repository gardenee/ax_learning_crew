"""get_landmark tool — 이름/별칭 → 좌표 룩업.

외부 지오코딩 API 대신 자주 언급되는 랜드마크(사무실 동, 지하철역)를
하드코딩 dict 로 관리한다. LG 사이언스파크 E13/E14 중심 반경 기준.

새 랜드마크 추가는 `LANDMARKS` dict 한 곳만 건드리면 된다.
"""
from __future__ import annotations


# 좌표는 사용자 검증 값.
LANDMARKS: dict[str, dict] = {
    "lg_sciencepark_e13": {
        "canonical_name": "LG사이언스파크 E13동",
        "lat": 37.561793,
        "lng": 126.835308,
        "aliases": [
            "e13", "e13동", "13동", "사무동", "본사",
            "사이언스파크", "lg사이언스파크", "사이언스파크 e13",
        ],
    },
    "lg_sciencepark_e14": {
        "canonical_name": "LG사이언스파크 E14동",
        "lat": 37.562990,
        "lng": 126.835500,
        "aliases": [
            "e14", "e14동", "14동", "연구동", "사이언스파크 e14",
        ],
    },
    "magok_station": {
        "canonical_name": "마곡역 (5호선)",
        "lat": 37.560301,
        "lng": 126.824939,
        "aliases": ["마곡", "마곡역"],
    },
    "magoknaru_station": {
        "canonical_name": "마곡나루역 (9호선/공항철도)",
        "lat": 37.566773,
        "lng": 126.827817,
        "aliases": ["마곡나루", "마곡나루역"],
    },
    "balsan_station": {
        "canonical_name": "발산역 (5호선)",
        "lat": 37.558585,
        "lng": 126.837649,
        "aliases": ["발산", "발산역"],
    },
}


def _normalize(s: str) -> str:
    return "".join(s.lower().split())


# alias → key 역인덱스 (모듈 로드 시 한 번 구축).
_ALIAS_INDEX: dict[str, str] = {}
for _key, _info in LANDMARKS.items():
    _ALIAS_INDEX[_normalize(_key)] = _key
    _ALIAS_INDEX[_normalize(_info["canonical_name"])] = _key
    for _a in _info["aliases"]:
        _ALIAS_INDEX[_normalize(_a)] = _key


def resolve(name: str) -> str | None:
    """사용자 발화 단어 → landmark key. 못 찾으면 None."""
    n = _normalize(name)
    if n in _ALIAS_INDEX:
        return _ALIAS_INDEX[n]
    # 부분일치 fallback: 별칭이 발화에 포함된 경우
    for alias_norm, key in _ALIAS_INDEX.items():
        if len(alias_norm) >= 2 and alias_norm in n:
            return key
    return None


def handle(name: str) -> dict:
    key = resolve(name)
    if key is None:
        return {
            "error": f"랜드마크를 찾지 못했습니다: {name!r}",
            "candidates": [
                {"key": k, "canonical_name": v["canonical_name"], "aliases": v["aliases"]}
                for k, v in LANDMARKS.items()
            ],
        }
    info = LANDMARKS[key]
    return {
        "key": key,
        "canonical_name": info["canonical_name"],
        "lat": info["lat"],
        "lng": info["lng"],
    }
