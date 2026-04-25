"""update_user_memory tool — 대화 중 알게 된 선호를 Postgres 에 기록 (write).

에이전트가 *"해산물 싫어"*, *"어제 OO국밥 별로였어"* 같은 명시적 선호 발화를
감지하면 호출한다. 서비스 계층의 `record_preference` 로 `preference_signals`
테이블에 한 건을 쌓는다.

──────────────────────────────────────────────────────────────
크루원 수정 포인트가 보이면 `# [student-edit]` 주석을 찾아가세요.
토글은 `tool_memory` 하나로 read/write 둘 다 묶어서 끕니다.
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations


def handle(
    user_id: str,
    signal_type: str,
    concept_key: str | None = None,
    restaurant_place_id: str | None = None,
    restaurant_name: str | None = None,
) -> dict:
    """user_id 사용자의 선호를 한 건 기록한다.

    Args:
      user_id:              선호의 주체 (UUID 문자열).
      signal_type:          "likes" 또는 "dislikes".
      concept_key:          concepts.key (예: "soup", "seafood"). 메뉴/카테고리 선호일 때.
      restaurant_place_id:  Qdrant payload 의 Google Place ID 문자열. 특정 식당 선호일 때.
      restaurant_name:      표시용 식당 이름 스냅샷 (Qdrant 왕복 없이 이름 노출).

    concept_key 와 restaurant_place_id 중 정확히 하나만 지정합니다.
    없는 concept_key 가 들어오면 신규 concept 을 만들어 연결합니다 (자동 확장).
    """
    from app.core.db import SessionLocal
    from app.services.memory.memory_service import record_preference

    with SessionLocal() as db:
        result = record_preference(
            db,
            user_id=user_id,
            signal_type=signal_type,
            concept_key=concept_key,
            restaurant_place_id=restaurant_place_id,
            restaurant_name=restaurant_name,
        )

    # [student-edit] LLM 에게 돌려줄 응답 형태를 바꿔 보세요.
    # 예: 기록 실패 시 어떻게 대응할지 / action 외에 "message" 한 줄을 추가해
    #     LLM 이 사용자에게 "'싫어함'으로 기록해둘게요" 라고 말하기 쉽게 만들기 등.
    return {
        "ok": True,
        "action": result["action"],
        "signal_type": signal_type,
        "target": result["target"],
    }
