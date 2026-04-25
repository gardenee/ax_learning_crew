"""Memory 서비스 — get_user_memory / update_user_memory tool 의 응답을 조립한다.

repository 계층에서 raw 데이터를 모아, 에이전트가 한눈에 쓸 수 있는 구조로 합친다.

반환 구조:
- users : 사용자별 likes/dislikes/likedRestaurants/dislikedRestaurants + 최근 dislike reason
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.users import (
    get_preference_signals,
    get_recent_dislike_reasons,
    upsert_preference_signal,
)


def assemble_memory(db: Session, user_ids: list[str]) -> dict[str, Any]:
    """memory 페이로드를 조립한다."""
    signals = get_preference_signals(db, user_ids)
    dislike_reasons = get_recent_dislike_reasons(db, user_ids, days=30, limit_per_user=20)

    users: dict[str, dict[str, Any]] = {}
    for uid in user_ids:
        uid_key = str(uid)
        user_signals = signals.get(uid_key, {})
        users[uid_key] = {
            "likes": user_signals.get("likes", []),
            "dislikes": user_signals.get("dislikes", []),
            "likedRestaurants": user_signals.get("likedRestaurants", []),
            "dislikedRestaurants": user_signals.get("dislikedRestaurants", []),
            "recentDislikeReasons": dislike_reasons.get(uid_key, []),
        }

    return {"users": users}


def record_preference(
    db: Session,
    user_id: str,
    signal_type: str,
    *,
    concept_key: str | None = None,
    restaurant_place_id: str | None = None,
    restaurant_name: str | None = None,
) -> dict[str, Any]:
    """대화 중 알게 된 선호를 preference_signals 에 저장한다."""
    return upsert_preference_signal(
        db,
        user_id=user_id,
        signal_type=signal_type,
        concept_key=concept_key,
        restaurant_place_id=restaurant_place_id,
        restaurant_name=restaurant_name,
        source="agent",
    )
