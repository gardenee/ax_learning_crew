"""Feedback 서비스 — 카드 버튼을 데이터 층에 반영.

세션 6 "피드백 루프" 의 구현. 파이프 입구(버튼) 와 출구(get_user_memory) 는
이미 있고, 이 모듈이 둘 사이를 잇는다:

  FE 버튼 → POST /api/feedback → [이 모듈]
                                     │
                                     ├─ feedback_events.insert (로그)
                                     └─ preference_signals.upsert (상태, 조건부)
                                              │
                                              ▼
                               다음 턴 get_user_memory 가 읽어 자동 반영

## 분기 규칙

- `liked` → events append + signals upsert (식당 "좋아요" 상태)
- `disliked` + reason_tags 없음 → events append + signals upsert (식당 블랙리스트)
- `disliked` + reason_tags 있음 → events append 만. signals 는 건드리지 않는다.
    이유 있는 거부 (비쌈/멀다/최근 방문 등) 는 식당 자체를 블랙리스트 할 근거가
    못 된다. 다음 턴 get_user_memory 가 최근 dislike 이벤트를 함께 읽어
    LLM 이 "이 사람은 거리에 민감하구나" 같은 패턴을 자연어로 해석한다.
- `visited` → events append 만. 방문 사실은 선호 상태가 아니다.
- `clear=True` → events 는 건드리지 않고 signals 의 row 만 삭제 (토글 해제).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.feedback import (
    delete_restaurant_preference,
    insert_feedback_event,
    upsert_restaurant_preference,
)


def record_feedback(
    db: Session,
    *,
    user_id: str,
    candidate_place_id: str,
    candidate_name: str | None,
    verdict: str,
    reason_tags: list[str] | None = None,
    free_text: str | None = None,
    clear: bool = False,
) -> dict[str, Any]:
    """피드백 한 건을 반영하고 메타 정보를 반환한다."""
    if clear:
        preference = delete_restaurant_preference(
            db,
            user_id=user_id,
            place_id=candidate_place_id,
            verdict=verdict,
        )
        return {"event_id": None, "preference": preference}

    event_id = insert_feedback_event(
        db,
        user_id=user_id,
        candidate_place_id=candidate_place_id,
        verdict=verdict,
        reason_tags=reason_tags,
        free_text=free_text,
    )

    has_reason = bool(reason_tags) or bool(free_text)
    skip_signal_upsert = verdict == "visited" or (verdict == "disliked" and has_reason)

    if skip_signal_upsert:
        preference = {
            "action": "skipped",
            "reason": (
                "visited 는 선호 아님"
                if verdict == "visited"
                else "reason 이 있는 disliked 는 식당 블랙리스트 대상이 아님"
            ),
        }
    else:
        preference = upsert_restaurant_preference(
            db,
            user_id=user_id,
            place_id=candidate_place_id,
            restaurant_name=candidate_name,
            verdict=verdict,
        )
    return {"event_id": event_id, "preference": preference}
