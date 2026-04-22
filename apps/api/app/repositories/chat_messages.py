"""chat_messages 저장소 — Claude SDK messages 배열을 Postgres 에 스냅샷한다."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from app.repositories._db import run_in_session


def load_messages(session_id: UUID) -> list[dict]:
    """세션의 messages 배열을 turn_index 오름차순으로 반환한다.

    반환값은 Claude SDK messages 포맷 그대로
    """
    sql = text(
        """
        SELECT role, content
        FROM chat_messages
        WHERE session_id = :sid
        ORDER BY turn_index ASC
        """
    )

    def op(db):
        rows = db.execute(sql, {"sid": str(session_id)}).mappings().all()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    return run_in_session(
        op,
        default=[],
        error_msg=f"chat_messages load failed (session_id={session_id})",
    )


def save_messages(
    session_id: UUID,
    messages: list[dict],
    *,
    status: str = "completed",
) -> None:
    """세션의 messages 를 통째로 덮어쓴다 (DELETE + INSERT).

    status='aborted' 면 마지막 메시지 한 건만 'aborted' 로 기록한다.
    """
    del_sql = text("DELETE FROM chat_messages WHERE session_id = :sid")
    ins_sql = text(
        """
        INSERT INTO chat_messages (session_id, turn_index, role, content, status)
        VALUES (:sid, :idx, :role, CAST(:content AS JSONB), :status)
        """
    )

    last_idx = len(messages) - 1

    def op(db):
        db.execute(del_sql, {"sid": str(session_id)})
        for idx, msg in enumerate(messages):
            row_status = status if (status == "aborted" and idx == last_idx) else "completed"
            db.execute(
                ins_sql,
                {
                    "sid": str(session_id),
                    "idx": idx,
                    "role": msg.get("role"),
                    "content": json.dumps(msg.get("content"), ensure_ascii=False),
                    "status": row_status,
                },
            )
        db.commit()

    run_in_session(
        op,
        default=None,
        error_msg=f"chat_messages save failed (session_id={session_id})",
    )
