"""Tool 정의 및 핸들러 레지스트리.

────────────────────────────────────────────────────────────────
크루원 안내: 이 파일은 **완성본** 으로 제공됩니다.
각 세션의 핵심 학습 포인트(tool 로직과 프롬프트 설계) 에 집중하기 위해
등록 boilerplate 는 건드리지 않아도 됩니다.

새 tool 을 직접 추가할 때는 아래 패턴을 따르세요:
1. `app/tools/<name>.py` 에 `handle(...)` 구현
2. `TOOL_DEFINITIONS` 에 Claude API tool 스키마(JSON Schema) append
3. `TOOL_HANDLERS` 에 name → handler 매핑 추가
4. 해당 세션 프롬프트에 사용 규칙 서술
5. (선택) `apps/web/src/lib/session-flags.ts` + `runner._TOOL_GROUPS` 에
   토글 flag 추가
────────────────────────────────────────────────────────────────
"""

import logging

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS: list[dict] = []
TOOL_HANDLERS: dict[str, callable] = {}


from app.tools import memory as memory_tool
from app.tools import memory_update as memory_update_tool

TOOL_DEFINITIONS.append(
    {
        "name": "get_user_memory",
        "description": (
            "사용자의 저장된 선호(메뉴 likes/dislikes, 좋아/싫어하는 식당), "
            "제약(예산/이동시간/식사시간), 최근 식사 이력을 한 번에 조회한다. "
            "사용자 맥락이 필요한 추천/결정 흐름에서는 **추천을 생성하기 전에** 반드시 호출한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "조회할 사용자 UUID 목록",
                },
            },
            "required": ["user_ids"],
        },
    }
)

TOOL_DEFINITIONS.append(
    {
        "name": "update_user_memory",
        "description": (
            "사용자가 대화에서 선호/비선호를 **명시적으로** 표현했을 때 그 사실을 "
            "`preference_signals` 에 한 건 기록한다. 다음 대화(심지어 다른 세션)에서도 "
            "`get_user_memory` 로 다시 꺼내 쓸 수 있게 된다. "
            "호출 타이밍 예시: "
            "  '나 해산물 싫어'             → signal_type='dislikes', concept_key='seafood' "
            "  '국물 요리 좋아해'            → signal_type='likes',    concept_key='soup' "
            "  '어제 OO국밥 별로였어'        → signal_type='dislikes', restaurant_place_id='<Google Place ID>', restaurant_name='OO국밥' "
            "concept_key 와 restaurant_place_id 중 정확히 **하나만** 채운다. "
            "restaurant_place_id 는 search_restaurants 결과의 candidate.restaurant_id 를 그대로 쓴다. "
            "사용자가 추측 또는 가정을 말한 경우(예: '국물 좋을지도?') 에는 호출하지 말 것 — "
            "메모리 오염을 방지한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "선호를 기록할 사용자 UUID (participant_ids[0])",
                },
                "signal_type": {
                    "type": "string",
                    "enum": ["likes", "dislikes"],
                    "description": "이 선호가 긍정인지 부정인지",
                },
                "concept_key": {
                    "type": "string",
                    "description": (
                        "메뉴/카테고리 선호일 때 concept 키. 예: 'soup', 'seafood', 'noodle'. "
                        "없는 키면 새 concept 이 만들어진다. restaurant_place_id 와 동시에 지정 금지."
                    ),
                },
                "restaurant_place_id": {
                    "type": "string",
                    "description": (
                        "특정 식당 선호일 때 Google Place ID 문자열 "
                        "(search_restaurants 결과의 restaurant_id). concept_key 와 동시에 지정 금지."
                    ),
                },
                "restaurant_name": {
                    "type": "string",
                    "description": (
                        "표시용 식당 이름 스냅샷. restaurant_place_id 와 함께 넘기면 "
                        "나중 조회에서 Qdrant 왕복 없이 이름이 바로 표시된다."
                    ),
                },
            },
            "required": ["user_id", "signal_type"],
        },
    }
)

TOOL_HANDLERS["get_user_memory"] = memory_tool.handle
TOOL_HANDLERS["update_user_memory"] = memory_update_tool.handle


from app.tools import search as search_tool
from app.tools import search_menus as search_menus_tool

_FILTER_SCHEMA = {
    "type": "object",
    "description": (
        "memory 에서 뽑은 제약 + 현재 위치 근처 조건을 검색 단계에 주입한다. "
        "`exclude_keywords` 는 사용자 dislikes 중 태그/메뉴명으로 표현 가능한 한국어 키워드. "
        "`exclude_restaurant_ids` 는 최근 식사 이력 place_id (어제랑 다른 거 효과). "
        "`near` 는 중심 좌표 + 반경 (meters) — 'E13동 800m 안' 같은 hard filter. "
        "`budget_max`/`min_rating` 은 숫자 후처리 필터."
    ),
    "properties": {
        "exclude_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Qdrant payload 의 tags/dish_types 에 매칭되는 한국어 키워드 목록. "
                "예: ['해산물', '회'] → 이 키워드가 태그에 걸린 식당 제외."
            ),
        },
        "exclude_restaurant_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "제외할 식당 place_id 목록 (Google Place ID 문자열). "
                "memory.users[*].dislikedRestaurants 의 placeId 를 그대로 넣으면 "
                "싫어하는 집이 후보에서 빠진다."
            ),
        },
        "near": {
            "type": "object",
            "description": (
                "중심 좌표 + 반경으로 후보를 좁힌다. 사용자가 'E13동 근처', "
                "'마곡역 5분 안' 처럼 장소 기반 제약을 걸면 get_landmark 로 좌표를 "
                "구한 뒤 여기에 넣는다. 거리 제약이 '도보 N분' 형태로 올 때는 "
                "`max_walk_minutes=N` 으로 넘기면 서비스가 1km=15분 기준으로 m 로 변환한다 "
                "(예: 도보 10분 이내 → max_walk_minutes=10). 둘 다 오면 분이 우선. "
                "기본 반경은 800m."
            ),
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "max_walk_minutes": {
                    "type": "number",
                    "description": (
                        "도보 N분 이내 하드 필터. 1km=15분 (≈ 67m/min) 기준으로 m 로 환산된다. "
                        "사용자가 '도보 10분 안', '5분 안쪽' 처럼 시간 단위로 거리 제약을 걸 때 쓴다."
                    ),
                },
                "radius_m": {
                    "type": "number",
                    "default": 800,
                    "description": "수동 반경 (m). max_walk_minutes 가 없을 때만 쓰인다.",
                },
            },
            "required": ["lat", "lng"],
        },
        "budget_max": {"type": "integer", "description": "메뉴 최고 가격 상한 (원)"},
        "min_rating": {"type": "number", "description": "평점 하한 (0~5)"},
    },
}

TOOL_DEFINITIONS.append(
    {
        "name": "search_menus",
        "description": (
            "**1단계 추천 (음식 결정)** 에 쓰는 메뉴 검색 tool. "
            "사용자가 '뭐 먹지?', '오늘 점심 뭐 좋을까' 처럼 **식당 전에 음식부터 정하려는 단계** "
            "일 때 호출한다. 자연어 query 를 Qdrant `menus` 컬렉션에 던져 "
            "벡터 유사도 높은 메뉴들을 가져오고 메뉴명 단위로 dedupe 해서 반환한다 "
            "(예: '칼국수', '국밥', '비빔밥' — 카드 여러 개). "
            "사용자가 '칼국수로 해줘' 같이 메뉴를 확정하면 이후 search_restaurants 로 넘어간다. "
            "개인 선호가 필요하면 이 tool 보다 먼저 get_user_memory 를 호출한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "사용자의 상황/기분을 한 줄 자연어로. 예: '비 오는 날 따뜻한 거', '가볍고 빨리'",
                },
                "top_k": {"type": "integer", "default": 5, "description": "메뉴 후보 수"},
                "filter": _FILTER_SCHEMA,
                "use_rerank": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "True 면 vector + keyword + popularity 신호로 재정렬. "
                        "같은 '국수류' 가 상위에 몰려 순서가 모호할 때 특히 효과."
                    ),
                },
                "rerank_weights": {
                    "type": "object",
                    "description": "신호별 가중치 override. 예: {'keyword': 1.0}",
                    "properties": {
                        "vector": {"type": "number"},
                        "keyword": {"type": "number"},
                        "popularity": {"type": "number"},
                    },
                },
            },
            "required": ["query"],
        },
    }
)

TOOL_DEFINITIONS.append(
    {
        "name": "search_restaurants",
        "description": (
            "**2단계 추천 (식당 결정)** 에 쓰는 식당 검색 tool. "
            "사용자가 메뉴를 정했거나(예: '칼국수로!'), 처음부터 식당을 원할 때 호출한다. "
            "Qdrant `restaurants` 컬렉션에서 의미 유사도 높은 식당 top_k 를 가져온다. "
            "추천 응답에 나오는 식당 이름/카테고리/근거는 **반드시 이 tool 결과의 payload 에서 인용** 해야 한다 — "
            "LLM 이 아는 식당을 임의로 지어내지 말 것. "
            "memory 가 있으면 dislikes 는 filter.exclude_keywords 로(한국어 태그 매칭), "
            "dislikedRestaurants 의 placeId 는 filter.exclude_restaurant_ids 로, "
            "likes 는 boost_concepts 로 넘겨 개인화한다. "
            "사용자가 장소 기반 제약('E13동 근처', '마곡역 5분 이내') 을 주면 먼저 get_landmark 로 좌표를 받아 "
            "filter.near={lat, lng, max_walk_minutes|radius_m} 으로 넣으면 geo_radius 로 후보가 좁혀진다 "
            "(도보 N분 제약이면 max_walk_minutes=N)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 질의. 한 줄 자연어. 예: '칼국수 잘하는 집', '회식하기 좋은 고깃집'",
                },
                "top_k": {"type": "integer", "default": 5, "description": "식당 후보 수"},
                "filter": _FILTER_SCHEMA,
                "use_rerank": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "True 면 vector + keyword + popularity + memory 신호로 재정렬. "
                        "같은 메뉴의 식당이 여러 개 나와 점수 차가 작을 때 효과가 크다."
                    ),
                },
                "rerank_weights": {
                    "type": "object",
                    "description": (
                        "신호별 가중치 override. '인기 있는 집' 힌트가 강하면 "
                        "{'popularity': 0.8}, '정확 매칭' 이 중요하면 {'keyword': 1.0}."
                    ),
                    "properties": {
                        "vector": {"type": "number"},
                        "keyword": {"type": "number"},
                        "popularity": {"type": "number"},
                        "memory": {"type": "number"},
                    },
                },
                "boost_concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "memory.users[*].likes (concept_key 목록) 를 그대로 넘긴다. "
                        "rerank 에서 해당 concept 이 식당 tags/dish_types 에 걸리면 가산점. "
                        "use_rerank=True 와 함께 써야 의미 있음."
                    ),
                },
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "여러 관점의 변주 쿼리를 한 번에 넘기면 각 쿼리로 독립 검색 후 "
                        "Reciprocal Rank Fusion 으로 합쳐 후보 풀을 넓힌다. 쿼리 간 겹쳐 "
                        "등장하는 식당이 상위로 올라와 '다각도에서 일관되게 좋은 집' 이 "
                        "뽑힌다. **첫 원소는 `query` 와 동일하게 명시적으로** 넣어라 "
                        "(원본 유지). 나머지는 memory.likes 반영, 날씨 반영, "
                        "분위기/상황 바꾸기 등 2~3개 변주. 포괄/모호 쿼리일수록 유용. "
                        "예: query='한식' 일 때 queries=['한식', '비 오는 날 국물 한식', "
                        "'든든한 집밥 스타일'] 같은 식."
                    ),
                },
                "randomness": {
                    "type": "number",
                    "default": 0.0,
                    "description": (
                        "0.0~1.0. 0 이면 결정적(항상 같은 순서). 높을수록 rerank_score "
                        "가 유사한 인접 후보들끼리 셔플되어 '비슷비슷한 1~2위' 가 호출마다 "
                        "섞인다 (seed 없음 = 매번 신선). 점수 차가 큰 후보의 순서는 보존. "
                        "memory 로 선호가 명확하면 0.1, 포괄/모호 쿼리는 0.3 권장."
                    ),
                },
            },
            "required": ["query"],
        },
    }
)

TOOL_HANDLERS["search_menus"] = search_menus_tool.handle
TOOL_HANDLERS["search_restaurants"] = search_tool.handle


from app.tools import weather as weather_tool

TOOL_DEFINITIONS.append(
    {
        "name": "get_weather",
        "description": (
            "현재 위치의 실시간 날씨(온도/체감/강수/상태)를 조회한다. "
            "사용자 발화에 비·눈·추위·더위·'지금'·'오늘' 같은 실시간성 단서가 있을 때 호출하라. "
            "맑고 평범한 날 단순 추천 질문에서는 호출하지 않아도 된다 — 필요한 만큼만."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude":  {"type": "number", "description": "위도 (서울 기본 37.5)"},
                "longitude": {"type": "number", "description": "경도 (서울 기본 127.0)"},
            },
            "required": ["latitude", "longitude"],
        },
    }
)

TOOL_HANDLERS["get_weather"] = weather_tool.handle


from app.tools import travel as travel_tool

TOOL_DEFINITIONS.append(
    {
        "name": "estimate_travel_time",
        "description": (
            "origin (현재 위치) 에서 destinations (식당 후보 리스트) 각각까지의 "
            "도보 이동거리·소요시간을 추정한다. "
            "search_restaurants 로 후보를 가져온 뒤, 사용자가 시간에 쫓기거나 이동 제약을 "
            "둔 경우 호출하라. 후보가 많을 땐 상위 3~5개만 넘겨도 충분하다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "object",
                    "description": "사용자 현재 위치",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                    },
                    "required": ["lat", "lng"],
                },
                "destinations": {
                    "type": "array",
                    "description": "식당 후보 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "lat":  {"type": "number"},
                            "lng":  {"type": "number"},
                        },
                        "required": ["lat", "lng"],
                    },
                },
            },
            "required": ["origin", "destinations"],
        },
    }
)

TOOL_HANDLERS["estimate_travel_time"] = travel_tool.handle


from app.tools import landmark as landmark_tool

TOOL_DEFINITIONS.append(
    {
        "name": "get_landmark",
        "description": (
            "사용자 발화에 나온 랜드마크 이름(사무실 동 이름, 지하철역 이름)을 위경도 좌표로 변환한다. "
            "현재 지원: LG사이언스파크 E13동/E14동, 마곡역, 마곡나루역, 발산역. "
            "별칭도 인식한다 — 'E13동', '13동', '사무동', '본사' → E13; 'E14동', '연구동' → E14. "
            "`estimate_travel_time` 의 origin 을 구할 때, 또는 `search_restaurants(filter.near)` 의 중심점을 "
            "잡을 때 먼저 호출한다. 모호하거나 지원 목록에 없으면 error + candidates 를 돌려주므로, "
            "그 경우 `ask_user` 로 되묻거나 E13 기본값으로 fallback 한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "사용자가 쓴 랜드마크 표현 그대로. 예: 'E13동', '마곡나루역', '연구동'.",
                },
            },
            "required": ["name"],
        },
    }
)

TOOL_HANDLERS["get_landmark"] = landmark_tool.handle


from app.tools import clarify as clarify_tool

TOOL_DEFINITIONS.append(
    {
        "name": "ask_user",
        "description": (
            "사용자에게 **여러 정보를 한 번에 묶어** 묻고 싶을 때 호출한다. "
            "runner 가 각 field 를 input block(text_input / number_input / chips_input / select_input) 으로 변환해 "
            "프런트에 흘려보내고 `submit_button` 을 덧붙인 뒤 루프를 끝낸다. "
            "사용자가 제출하면 같은 session_id 로 재호출되어 form_answers 와 함께 대화가 이어진다. "
            "단, 다음 경우에는 쓰지 말 것: "
            "  - 한 가지 속성만 애매 → 응답 JSONL 에 `choice_chips` 하나만 넣는다. "
            "  - 한 줄 자연어로 되물을 수 있음 → 그냥 `message` 로 질문하고 사용자 응답을 기다린다. "
            "  - 이미 한 번 물었거나 form_answers 가 이번 입력에 들어있다 → 다시 부르지 말 것."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "왜 물어봐야 하는지 한국어 한 줄 — 폼 상단 message block 으로 표시된다",
                },
                "fields": {
                    "type": "array",
                    "description": (
                        "3개 이하. 각 항목 { kind, name, label, required?, helper_text?, "
                        "placeholder?, min?, max?, unit?, options? }. "
                        "kind 는 FE input block 으로 매핑된다: "
                        "text→text_input, number→number_input, select→select_input, "
                        "chips→chips_input(단일선택), multi-select→chips_input(다중선택)."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": ["text", "number", "select", "multi-select", "chips"],
                            },
                            "name": {"type": "string", "description": "필드 식별자 (영문 snake_case)"},
                            "label": {"type": "string", "description": "라벨 (한국어)"},
                            "required": {"type": "boolean"},
                            "helper_text": {"type": "string"},
                            "placeholder": {"type": "string"},
                            "min": {"type": "number"},
                            "max": {"type": "number"},
                            "unit": {"type": "string", "description": "number_input 뒤에 붙는 단위 표기 (예: 원, 분)"},
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "value": {"type": "string"},
                                    },
                                    "required": ["label", "value"],
                                },
                            },
                        },
                        "required": ["kind", "name", "label"],
                    },
                },
            },
            "required": ["reason", "fields"],
        },
    }
)

TOOL_HANDLERS["ask_user"] = clarify_tool.handle


from app.tools import evaluate as evaluate_tool

TOOL_DEFINITIONS.append(
    {
        "name": "evaluate_response",
        "description": (
            "추천 카드를 최종 응답에 포함하기 **직전** 에 호출해 자기 응답을 평가한다. "
            "두 가지를 동시에 체크한다: "
            "(1) **근거 검증** — 각 카드의 `place_id` 가 이번 세션의 search_restaurants "
            "결과에 실제로 있었는지 rule-based 로 확인 (LLM 이 지어낸 식당 차단). "
            "(2) **요구사항 검증** — LLM-as-judge 가 user_requirements 와 recommendations 를 "
            "비교해 의미적 위반 감지. "
            "둘 중 하나라도 걸리면 tool 이 alert_card 를 FE 로 직접 띄우므로, LLM 은 alert 내용을 "
            "응답에 중복으로 적지 말고 재검색/카드 제거/사유 설명 중 하나로 대응한다. "
            "user_requirements 가 비어있어도 근거 검증은 돌아간다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "사용자가 말한 제약/선호의 자연어 문장 리스트. "
                        "예: ['1만원 이하', '해산물 제외', '도보 10분 안']. "
                        "user_message / form_answers / constraints 에서 뽑아낸다."
                    ),
                },
                "recommendations": {
                    "type": "array",
                    "description": "최종 응답에 담을 추천 카드의 요약 리스트",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "place_id": {
                                "type": "string",
                                "description": (
                                    "search_restaurants 결과의 candidate.restaurant_id 를 "
                                    "**그대로 복사** 해서 넣는다. 이 값이 이번 세션의 검색 "
                                    "결과에 없으면 '근거 없는 추천' 으로 판정된다. "
                                    "식당 카드를 뱉을 거면 반드시 채울 것 — 비면 환각 위반."
                                ),
                            },
                            "category": {"type": "string"},
                            "walk_minutes": {"type": "number"},
                            "budget_label": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "place_id"],
                    },
                },
            },
            "required": ["user_requirements", "recommendations"],
        },
    }
)

TOOL_HANDLERS["evaluate_response"] = evaluate_tool.handle


def execute_tool(name: str, input_data: dict, session=None) -> dict:
    """Tool 이름으로 핸들러를 찾아 실행한다."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        extra: dict = {}
        if name == "evaluate_response" and session is not None:
            extra["known_place_ids"] = sorted(getattr(session, "known_place_ids", set()))
        return handler(**input_data, **extra)
    except Exception as exc:  # noqa: BLE001
        logger.exception("tool %s execution failed", name)
        return {"error": str(exc), "tool": name}
