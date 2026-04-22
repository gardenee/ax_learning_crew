"""POST /api/feedback — 카드 하단 👍/👎 버튼을 받아 데이터 층에 반영한다."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core.db import SessionLocal
from app.models.request_models import FeedbackRequest
from app.services.feedback.feedback_service import record_feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
def submit_feedback(req: FeedbackRequest):
    try:
        with SessionLocal() as db:
            result = record_feedback(
                db,
                user_id=str(req.user_id),
                candidate_place_id=req.candidate_restaurant_id,
                candidate_name=req.candidate_restaurant_name,
                verdict=req.verdict,
                reason_tags=req.reason_tags,
                free_text=req.free_text,
                clear=req.clear,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("feedback persist failed")
        raise HTTPException(status_code=500, detail=f"feedback persist failed: {exc}") from exc

    return {"status": "ok", **result}
