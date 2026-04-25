"""get_user_memory tool — 사용자 선호 조회 (read 전용).

이 파일은 얇은 어댑터다. 실제 조립 로직은 서비스 계층에 있다:
- `app.repositories.users`             — SQL 쿼리 (preference signals / feedback reasons)
- `app.services.memory.memory_service` — 조립

read 와 write 가 파일 경계로 분리되어 있다는 감각도 함께 익히자.
write 쪽은 `app.tools.memory_update` 에 있다.

──────────────────────────────────────────────────────────────
크루원 수정 포인트가 보이면 `# [student-edit]` 주석을 찾아가세요.
이 tool 은 기본 완성본입니다. 세션 플래그(`tool_memory`)로 껐다 켤 수 있습니다.
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations


def handle(user_ids: list[str]) -> dict:
    """user_ids 의 memory 를 조회해 반환한다.

    assemble_memory 가 만들어주는 응답 구조:
      {
        "users": {
          "<uuid>": {
            "likes": [...], "dislikes": [...],
            "likedRestaurants": [...], "dislikedRestaurants": [...],
            "recentDislikeReasons": [...]
          }
        }
      }
    """
    from app.core.db import SessionLocal
    from app.services.memory.memory_service import assemble_memory

    with SessionLocal() as db:
        result = assemble_memory(db, user_ids)

        # [student-edit] LLM 에게 보낼 payload 를 입맛대로 다듬어 보세요.
        # 예: recentDislikeReasons 를 최근 N 건만 남긴다 / likedRestaurants 를
        #     상위 3개로 제한한다 / 원하지 않는 키는 드롭한다 등.
        # LLM context window 를 아낄지 풍부한 맥락을 줄지 trade-off 를 체감할 수 있습니다.
        return result
