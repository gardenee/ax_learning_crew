"""Memory 서비스 — get_user_memory / update_user_memory tool 의 응답을 조립한다.

repository 계층에서 raw 데이터를 모아, 에이전트가 한눈에 쓸 수 있는 구조로 합친다.

반환 구조:
- users                     : 사용자별 프로필 + likes/dislikes + likedRestaurants/dislikedRestaurants + recentMeals
- groupConstraints          : (그룹 모드일 때) 전원 merge 결과
- projectPreset             : (project_id 주어졌을 때만) 프리셋

설계 원칙:
- dislikes 는 OR        (누구라도 싫어하면 그룹 전체의 hardExclude)
- likes   는 UNION      (전원의 선호 합집합 → softPreference)
- 식당 dislikes 는 식당 단위 hardExcludeRestaurants 로 별도 분리 (concept 과 구분)
- 식당 likes 는 softPreferredRestaurants 로
- 최근 3일 이내 방문 식당은 repeatPenalty (싫다는 게 아니라 "어제 먹었잖아")
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.users import (
    get_preference_signals,
    get_project_preset,
    get_recent_dislike_reasons,
    get_recent_meals,
    get_user_profiles,
    upsert_preference_signal,
)

_REPEAT_PENALTY_DAYS = 3


def assemble_memory(
    db: Session,
    user_ids: list[str],
    group_id: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """memory 페이로드를 조립한다."""
    profiles = get_user_profiles(db, user_ids)
    signals = get_preference_signals(db, user_ids)
    meals = get_recent_meals(db, user_ids, days=7)
    dislike_reasons = get_recent_dislike_reasons(db, user_ids, days=30, limit_per_user=20)

    users: dict[str, dict[str, Any]] = {}
    for uid in user_ids:
        uid_key = str(uid)
        user_signals = signals.get(uid_key, {})
        users[uid_key] = {
            **profiles.get(uid_key, {}),
            "likes": user_signals.get("likes", []),
            "dislikes": user_signals.get("dislikes", []),
            "likedRestaurants": user_signals.get("likedRestaurants", []),
            "dislikedRestaurants": user_signals.get("dislikedRestaurants", []),
            "recentMeals": meals.get(uid_key, []),
            "recentDislikeReasons": dislike_reasons.get(uid_key, []),
        }

    result: dict[str, Any] = {"users": users}

    if group_id and len(user_ids) > 1:
        result["groupConstraints"] = _merge_group_constraints(users)

    if project_id:
        preset = get_project_preset(db, project_id)
        if preset:
            result["projectPreset"] = preset

    return result


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


def _merge_group_constraints(users: dict[str, dict[str, Any]]) -> dict[str, list[Any]]:
    """그룹 전원의 선호를 하나의 제약 세트로 합친다."""
    hard_excludes: set[str] = set()
    soft_preferences: set[str] = set()
    hard_exclude_restaurants: dict[str, str] = {}   # placeId → name
    soft_preferred_restaurants: dict[str, str] = {}
    repeat_penalty: set[str] = set()

    cutoff = datetime.now().date() - timedelta(days=_REPEAT_PENALTY_DAYS)

    for user_data in users.values():
        hard_excludes.update(user_data.get("dislikes", []))
        soft_preferences.update(user_data.get("likes", []))

        for r in user_data.get("dislikedRestaurants", []):
            hard_exclude_restaurants[r["placeId"]] = r.get("name") or ""
        for r in user_data.get("likedRestaurants", []):
            soft_preferred_restaurants[r["placeId"]] = r.get("name") or ""

        for meal in user_data.get("recentMeals", []):
            meal_date = _parse_date(meal.get("date"))
            restaurant = meal.get("restaurant")
            if meal_date and restaurant and meal_date >= cutoff:
                repeat_penalty.add(restaurant)

    return {
        "hardExcludes": sorted(hard_excludes),
        "softPreferences": sorted(soft_preferences),
        "hardExcludeRestaurants": [
            {"placeId": pid, "name": name} for pid, name in sorted(hard_exclude_restaurants.items())
        ],
        "softPreferredRestaurants": [
            {"placeId": pid, "name": name} for pid, name in sorted(soft_preferred_restaurants.items())
        ],
        "repeatPenalty": sorted(repeat_penalty),
    }


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None
