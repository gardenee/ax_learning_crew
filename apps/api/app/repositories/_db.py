"""Repository 계층용 DB helper.
트랜잭션 경계(`db.commit()`)는 op 내부에서 필요한 시점에 직접 호출한다.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from sqlalchemy.orm import Session

from app.core.db import SessionLocal

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_in_session(op: Callable[[Session], T], *, default: T, error_msg: str) -> T:
    """SessionLocal 을 열어 db를 실행한다."""
    try:
        with SessionLocal() as db:
            return op(db)
    except Exception:  # noqa: BLE001
        logger.exception(error_msg)
        return default
