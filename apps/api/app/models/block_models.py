"""Structured block types — 에이전트 응답의 기본 단위."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EvidenceSnippet(BaseModel):
    label: str
    text: str
    source_type: Literal["menu", "review", "summary", "memory", "live-context", "situation_hint"]


class RestaurantSummary(BaseModel):
    id: str
    name: str
    category: str
    walk_minutes: int | None = None
    budget_label: str | None = None
    estimated_meal_minutes: int | None = None


class CompareAxis(BaseModel):
    label: str
    values: list[str]


class QuickAction(BaseModel):
    key: str
    label: str
    patch: dict


# --- Block types ---


class MessageBlock(BaseModel):
    type: Literal["message"] = "message"
    text: str


class RecommendationCardBlock(BaseModel):
    type: Literal["recommendation_card"] = "recommendation_card"
    rank: int
    restaurant: RestaurantSummary
    reason: str
    evidence: list[EvidenceSnippet] = []


class ComparisonTableBlock(BaseModel):
    type: Literal["comparison_table"] = "comparison_table"
    candidates: list[str]
    axes: list[CompareAxis]


class QuickActionsBlock(BaseModel):
    type: Literal["quick_actions"] = "quick_actions"
    actions: list[QuickAction]


class ContextSummaryBlock(BaseModel):
    type: Literal["context_summary"] = "context_summary"
    applied: list[str]


class FormFieldOption(BaseModel):
    label: str
    value: str


class FormField(BaseModel):
    kind: str
    name: str
    label: str
    required: bool = False
    helper_text: str | None = None
    min: int | None = None
    max: int | None = None
    default_value: str | int | list[str] | None = None
    options: list[FormFieldOption] | None = None


class FormSection(BaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    fields: list[FormField]


class FormBlock(BaseModel):
    type: Literal["form"] = "form"
    id: str
    title: str
    sections: list[FormSection]
    submit_label: str = "다음"


Block = (
    MessageBlock
    | RecommendationCardBlock
    | ComparisonTableBlock
    | QuickActionsBlock
    | ContextSummaryBlock
    | FormBlock
)
