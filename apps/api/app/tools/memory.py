"""get_user_memory tool — 사용자/그룹 선호 조회 (read 전용).

조회/조립 로직은 두 계층에 분리되어 있고 이 파일은 얇은 어댑터다:
- `app.repositories.users`             — SQL 쿼리
- `app.services.memory.memory_service` — 조립 + group merge

write 는 `app.tools.memory_update` 에 분리되어 있다.
"""

from __future__ import annotations


def handle(
    user_ids: list[str],
    group_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    """user_ids 의 memory 를 조회해 반환한다.

    assemble_memory 가 만들어주는 응답 구조:
      {
        "users": {
          "<uuid>": {
            "displayName": ..., "likes": [...], "dislikes": [...],
            "likedRestaurants": [...], "dislikedRestaurants": [...],
            "recentMeals": [...]
          }
        },
        "groupConstraints": {
          "hardExcludes": [...], "softPreferences": [...],
          "hardExcludeRestaurants": [...], "softPreferredRestaurants": [...],
          "repeatPenalty": [...]
        },
        "projectPreset": { ... }   # project_id 가 주어졌을 때만
      }
    """
    from app.core.db import SessionLocal
    from app.services.memory.memory_service import assemble_memory

    with SessionLocal() as db:
        return assemble_memory(
            db,
            user_ids,
            group_id=group_id,
            project_id=project_id,
        )
