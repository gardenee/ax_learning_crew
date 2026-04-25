"""feedback_events insert + preference_signals 식당 레벨 upsert.

세션 6 의 **데이터 층 반영(reflection)** 을 담당하는 SQL 계층.

## 왜 두 테이블에 동시에 쓰는가

`feedback_events` 는 **원시 이벤트 로그** 다 — 누가 언제 어떤 카드에 👍/👎 눌렀는지
append-only 로 남겨 분석에 쓴다.

`preference_signals` 는 **현재 선호 상태** 다 — `get_user_memory` 가 읽어 다음 추천에
반영하는 쪽. 여기에 upsert 를 해야 버튼 클릭이 곧바로 추천 동작으로 돌아온다.

파이프 구조:

  👍 클릭 → feedback_events (로그) + preference_signals (상태)
                                       │
                                       ▼
                         다음 턴 get_user_memory 가 읽어 반영

## 가중치 규칙

같은 식당 버튼을 여러 번 눌러도 의미가 있도록 `weight` 를 누적한다.

- 기존 row 없음             → INSERT (weight=1.0)
- 기존 row + 동일 verdict   → weight += 1.0 (cap 5.0)
- 기존 row + 반대 verdict   → 기존 row 제거 후 신규 INSERT (마음 바꿈)

"다섯 번 싫어요 ≠ 한 번 싫어요" 라는 신호 강도 차이를 표현하는 최소 구현.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_OPPOSITE: dict[str, str] = {"liked": "dislikes", "disliked": "likes"}
_VERDICT_TO_SIGNAL: dict[str, str] = {"liked": "likes", "disliked": "dislikes"}
_WEIGHT_CAP = 5.0


def delete_restaurant_preference(
    db: Session,
    *,
    user_id: str,
    place_id: str,
    verdict: str,
) -> dict[str, Any]:
    """해당 user + place_id + verdict→signal_type 의 row 를 지운다.

    feedback_events 는 append-only 로그이므로 건드리지 않는다.
    """
    if verdict not in _VERDICT_TO_SIGNAL:
        return {"action": "skipped", "reason": f"verdict={verdict} 는 signals 대상 아님"}

    signal_type = _VERDICT_TO_SIGNAL[verdict]
    deleted = db.execute(
        text(
            """
            DELETE FROM preference_signals
            WHERE owner_id = :uid
              AND signal_type = :st
              AND target_restaurant_place_id = :pid
            """
        ),
        {"uid": user_id, "st": signal_type, "pid": place_id},
    ).rowcount
    db.commit()
    return {"action": "cleared", "signal_type": signal_type, "deleted_rows": int(deleted or 0)}


def insert_feedback_event(
    db: Session,
    *,
    user_id: str,
    candidate_place_id: str,
    verdict: str,
    reason_tags: list[str] | None = None,
    free_text: str | None = None,
) -> str:
    """feedback_events 에 이벤트를 append한다."""
    sql = text(
        """
        INSERT INTO feedback_events
          (candidate_restaurant_place_id, verdict, reason_tags, free_text, created_by_user_id)
        VALUES
          (:place_id, :verdict, :tags, :free_text, :uid)
        RETURNING id
        """
    )
    row_id = db.execute(
        sql,
        {
            "place_id": candidate_place_id,
            "verdict": verdict,
            "tags": reason_tags or [],
            "free_text": free_text,
            "uid": user_id,
        },
    ).scalar()
    db.commit()
    return str(row_id)


def upsert_restaurant_preference(
    db: Session,
    *,
    user_id: str,
    place_id: str,
    restaurant_name: str | None,
    verdict: str,
) -> dict[str, Any]:
    """preference_signals 에 선호 상태를 upsert한다."""
    if verdict not in _VERDICT_TO_SIGNAL:
        return {"action": "skipped", "reason": f"verdict={verdict} 는 선호 반영 대상이 아님"}

    signal_type = _VERDICT_TO_SIGNAL[verdict]
    opposite_signal = _OPPOSITE[verdict]

    # 1) 반대 verdict row 가 있으면 제거
    deleted = db.execute(
        text(
            """
            DELETE FROM preference_signals
            WHERE owner_id = :uid
              AND signal_type = :st
              AND target_restaurant_place_id = :pid
            RETURNING id
            """
        ),
        {"uid": user_id, "st": opposite_signal, "pid": place_id},
    ).rowcount

    # 2) 같은 verdict row 가 있는지 확인
    existing = db.execute(
        text(
            """
            SELECT id, weight FROM preference_signals
            WHERE owner_id = :uid
              AND signal_type = :st
              AND target_restaurant_place_id = :pid
            LIMIT 1
            """
        ),
        {"uid": user_id, "st": signal_type, "pid": place_id},
    ).mappings().first()

    if existing:
        current_weight = float(existing["weight"] or 1.0)
        new_weight = min(current_weight + 1.0, _WEIGHT_CAP)
        db.execute(
            text(
                """
                UPDATE preference_signals
                SET weight = :w,
                    updated_at = now(),
                    target_restaurant_name = COALESCE(:rname, target_restaurant_name)
                WHERE id = :id
                """
            ),
            {"w": new_weight, "rname": restaurant_name, "id": str(existing["id"])},
        )
        db.commit()
        return {
            "action": "reinforced",
            "signal_type": signal_type,
            "weight": new_weight,
            "reverted_opposite": bool(deleted),
        }

    db.execute(
        text(
            """
            INSERT INTO preference_signals
              (owner_id, signal_type,
               target_restaurant_place_id, target_restaurant_name,
               source, weight)
            VALUES
              (:uid, :st, :pid, :rname, 'feedback_button', 1.0)
            """
        ),
        {
            "uid": user_id,
            "st": signal_type,
            "pid": place_id,
            "rname": restaurant_name,
        },
    )
    db.commit()
    return {
        "action": "inserted",
        "signal_type": signal_type,
        "weight": 1.0,
        "reverted_opposite": bool(deleted),
    }
