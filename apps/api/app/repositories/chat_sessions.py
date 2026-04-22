"""chat_sessions 테이블 저장소.

사이드바 "최근 대화"에 노출되는 세션 메타데이터를 관리한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.repositories._db import run_in_session


def upsert_session(
    session_id: UUID,
    *,
    title: str | None,
    mode: str | None,
    initiated_by_user_id: UUID | None,
) -> None:
    """세션을 생성하거나 title/updated_at을 갱신한다."""
    sql = text(
        """
        INSERT INTO chat_sessions (id, title, mode, initiated_by_user_id, updated_at)
        VALUES (:id, :title, :mode, :user_id, now())
        ON CONFLICT (id) DO UPDATE SET
          title = COALESCE(NULLIF(EXCLUDED.title, ''), chat_sessions.title),
          mode  = COALESCE(EXCLUDED.mode, chat_sessions.mode),
          updated_at = now()
        """
    )

    def op(db):
        db.execute(
            sql,
            {
                "id": str(session_id),
                "title": (title or "").strip() or None,
                "mode": mode,
                "user_id": str(initiated_by_user_id) if initiated_by_user_id else None,
            },
        )
        db.commit()

    run_in_session(
        op,
        default=None,
        error_msg=f"chat_sessions upsert failed (session_id={session_id})",
    )


def list_sessions(limit: int = 30) -> list[dict[str, Any]]:
    """최근 업데이트된 세션부터 최대 limit 건을 반환한다."""
    sql = text(
        """
        SELECT id, title, mode, updated_at, created_at
        FROM chat_sessions
        WHERE title IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT :limit
        """
    )

    def op(db):
        rows = db.execute(sql, {"limit": limit}).mappings().all()
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "mode": row["mode"],
                "updated_at": _iso(row["updated_at"]),
                "created_at": _iso(row["created_at"]),
            }
            for row in rows
        ]

    return run_in_session(op, default=[], error_msg="chat_sessions list failed")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
