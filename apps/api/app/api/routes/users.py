"""GET/POST /api/users/me — 단일 사용자 onboarding."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.db import SessionLocal

router = APIRouter(prefix="/api/users", tags=["users"])

# auth 가 붙기 전까지 "나" 로 취급하는 단일 user UUID.
CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_LOCATION_ALIAS = "E13동"


class UserMeResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    default_location_alias: str | None = None


class CreateMeRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


@router.get("/me", response_model=UserMeResponse)
def get_me():
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT id, handle, display_name, default_location_alias
                FROM users
                WHERE id = :id
                """
            ),
            {"id": CURRENT_USER_ID},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="not_onboarded")

    return UserMeResponse(
        id=str(row["id"]),
        handle=row["handle"],
        display_name=row["display_name"],
        default_location_alias=row["default_location_alias"],
    )


@router.post("/me", response_model=UserMeResponse)
def create_me(req: CreateMeRequest):
    display_name = req.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name_empty")

    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO users (id, handle, display_name, default_location_alias)
                VALUES (:id, :handle, :display_name, :location)
                ON CONFLICT (id) DO UPDATE
                  SET display_name = EXCLUDED.display_name
                """
            ),
            {
                "id": CURRENT_USER_ID,
                "handle": "me",
                "display_name": display_name,
                "location": DEFAULT_LOCATION_ALIAS,
            },
        )
        db.commit()

    return UserMeResponse(
        id=CURRENT_USER_ID,
        handle="me",
        display_name=display_name,
        default_location_alias=DEFAULT_LOCATION_ALIAS,
    )
