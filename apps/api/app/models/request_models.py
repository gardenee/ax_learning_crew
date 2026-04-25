from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RecommendationConstraints(BaseModel):
    budget_max: int | None = None
    max_walk_minutes: int | None = None
    max_meal_minutes: int | None = None


class SessionFlags(BaseModel):
    """세션 토글 드롭다운에서 끄고 켤 수 있는 플래그들.

    프런트 헤더의 톱니 아이콘 → 드롭다운 → 칩 토글로 바뀌며, 매 요청에 실려온다.
    값이 없거나 키가 빠진 경우는 모두 기본값(True)으로 동작한다.
    """

    remember_history: bool = True
    self_check: bool = True
    gen_ui: bool = True
    tool_memory: bool = True
    tool_search: bool = True
    tool_weather: bool = True
    tool_landmark: bool = True
    tool_travel: bool = True
    tool_ask_user: bool = True


class AgentRunRequest(BaseModel):
    session_id: UUID | None = None
    participant_ids: list[UUID] = []
    constraints: RecommendationConstraints | None = None
    user_message: str | None = None
    form_answers: dict | None = None
    constraint_patch: dict | None = None
    session_flags: SessionFlags | None = None


class FeedbackRequest(BaseModel):
    session_id: UUID | None = None
    user_id: UUID
    candidate_restaurant_id: str
    candidate_restaurant_name: str | None = None
    verdict: Literal["liked", "disliked", "visited"]
    reason_tags: list[str] = []
    free_text: str | None = None
    clear: bool = False
