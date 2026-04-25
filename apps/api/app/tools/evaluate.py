"""evaluate_response tool — LLM-as-judge 응답 평가기.

에이전트가 최종 응답을 뱉기 직전에 자기 응답을 스스로 채점하게 하는
self-reflection / guardrail 계층.

두 단계로 검증한다:
1. rule-based 환각 검사 — 각 recommendation 의 `place_id` 가 이번 세션의
   `search_restaurants` 결과에 있었던 id 인지 대조 (runner 가 넘기는
   `session.known_place_ids` 기반).
2. LLM-as-judge — 심사관 페르소나의 sub-agent 호출로 요구사항 vs 카드 요약을
   의미적으로 비교.

결과는 `emit_block` 키에 alert_card block 으로 실려 돌아간다. runner 는 이
키를 감지하면 LLM 을 거치지 않고 FE 로 직접 yield 한다:
- passed=True  → severity=success "응답 평가 통과"
- passed=False → severity=warning/error + 위반 목록
- 환각 검출    → title 을 "근거 없는 추천 감지" 로 교체

`ask_user` 의 `should_break_loop` 와 대칭되는 패턴 — ask_user 는 form 을
yield 한 뒤 루프 종료, evaluate 는 alert 만 yield 하고 루프는 이어간다.

──────────────────────────────────────────────────────────────
완성본. `self_check` 토글로 껐다 켤 수 있습니다 (evaluate_response + EVAL_RULES).
도전 과제: judge 프롬프트(`JUDGE_SYSTEM_PROMPT`)를 튜닝해 위반 탐지를 날카롭게.
추가 도전: rule-based 체크를 더 얹어보세요 (예: budget_max 숫자 비교).
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


JUDGE_SYSTEM_PROMPT = """\
너는 점심 추천 에이전트의 **응답 심사관** 이다.

입력으로 받은 `user_requirements` (사용자가 말한 요구사항 리스트) 와
`recommendations` (추천 카드 요약) 를 비교해, 각 요구사항이 **모든 카드에서
지켜졌는지** 판정한다.

- 숫자 제약(예산/시간) 은 정확히 비교한다.
- 자연어 조건("가까운 곳", "든든한") 은 카드의 category/tags/reason 을 바탕으로
  상식적으로 판단한다.
- 조금이라도 애매하면 **위반 아님** 으로 처리한다 (false positive 최소화).

반드시 다음 JSON 스키마로만 응답한다. 설명문·코드펜스 금지.

{
  "passed": true | false,
  "violations": [
    { "requirement": "<원문 요구사항>", "card": "<식당 이름>", "reason": "<왜 위반인지 한 줄>" }
  ],
  "verdict": "<전체 한 줄 요약. 위반 없으면 '모든 요구사항 충족'>"
}
"""


def handle(
    user_requirements: list[str],
    recommendations: list[dict],
    known_place_ids: list[str] | set[str] | None = None,
) -> dict:
    """추천 카드들이 요구사항을 지켰는지 + 실제 tool 결과에 근거했는지 판정.

    Args:
        user_requirements: 사용자 요구사항 자연어 리스트.
            예: ["1만원 이하", "해산물 제외", "도보 10분 안"]
        recommendations: 추천 카드 요약 리스트.
            각 항목: {name, place_id, category?, walk_minutes?,
                      budget_label?, tags?}
        known_place_ids: 이번 세션에서 `search_restaurants` 가 반환한
            restaurant_id 집합. runner 가 session 에서 주입. None 이면
            환각 검사를 건너뛴다.

    Returns:
        {passed, violations[], verdict, emit_block}
    """
    known_set: set[str] | None = (
        set(known_place_ids) if known_place_ids is not None else None
    )
    hallucinations = _check_hallucinations(recommendations, known_set)

    # judge 는 요구사항·카드 둘 중 하나라도 비면 건너뛴다.
    if not user_requirements or not recommendations:
        judge_passed = True
        judge_violations: list[dict[str, str]] = []
        judge_verdict = "검증 대상 없음 — 명시적 요구사항이나 후보 카드가 없습니다."
    else:
        try:
            raw = _call_judge(
                {
                    "user_requirements": user_requirements,
                    "recommendations": recommendations,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("evaluate_response judge call failed: %s", exc)
            fallback_verdict = f"심사관 호출 실패 — 검증 건너뜀 ({exc})"
            # 환각이 이미 있으면 그건 그대로 반영; judge 실패는 info 톤으로.
            if hallucinations:
                return _compose_result(hallucinations, [], fallback_verdict)
            return {
                "passed": True,
                "violations": [],
                "verdict": fallback_verdict,
                "emit_block": {
                    "type": "alert_card",
                    "severity": "info",
                    "title": "응답 평가 건너뜀",
                    "summary": fallback_verdict,
                    "items": [],
                },
            }

        normalized = _normalize_verdict(raw)
        judge_passed = normalized["passed"]
        judge_violations = normalized["violations"]
        judge_verdict = normalized["verdict"]

    return _compose_result(hallucinations, judge_violations, judge_verdict, judge_passed=judge_passed)


def _check_hallucinations(
    recommendations: list[dict], known_place_ids: set[str] | None
) -> list[dict[str, str]]:
    """각 recommendation 의 place_id 가 실제 tool 결과에 있었는지 확인.

    known_place_ids=None 이면 검사하지 않는다 (legacy 경로).
    """
    if known_place_ids is None:
        return []

    violations: list[dict[str, str]] = []
    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        name = str(rec.get("name") or "?")
        place_id = rec.get("place_id")
        if not place_id:
            violations.append(
                {
                    "requirement": "근거 기반 추천 (tool 결과)",
                    "card": name,
                    "reason": "place_id 누락 — search_restaurants 결과와 대조할 수 없음",
                }
            )
            continue
        if place_id not in known_place_ids:
            violations.append(
                {
                    "requirement": "근거 기반 추천 (tool 결과)",
                    "card": name,
                    "reason": f"search_restaurants 결과에 없는 place_id ({place_id})",
                }
            )
    return violations


def _compose_result(
    hallucinations: list[dict[str, str]],
    judge_violations: list[dict[str, str]],
    judge_verdict: str,
    *,
    judge_passed: bool = True,
) -> dict:
    """환각 + judge violation 을 합쳐 최종 결과 dict 를 만든다."""
    all_violations = hallucinations + judge_violations
    passed = judge_passed and not hallucinations and not judge_violations

    if hallucinations:
        parts = [f"근거 없는 추천 {len(hallucinations)}건"]
        if judge_violations:
            parts.append(f"요구사항 위반 {len(judge_violations)}건")
        verdict = " + ".join(parts)
        title = "근거 없는 추천 감지"
    else:
        verdict = judge_verdict
        title = None  # _build_alert_block 의 기본 title 사용

    return {
        "passed": passed,
        "violations": all_violations,
        "verdict": verdict,
        "emit_block": _build_alert_block(
            verdict, all_violations, passed=passed, title_override=title
        ),
    }


def _call_judge(payload: dict[str, Any]) -> dict[str, Any]:
    """심사관 sub-agent 호출. JSON 파싱 후 raw dict 반환."""
    from app.core.config import settings
    from app.core.llm_client import get_client

    client = get_client()
    response = client.messages.create(
        model=settings.model_id,
        max_tokens=1024,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            }
        ],
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    # 코드펜스 벗겨내기 (LLM 이 실수로 ```json ... ``` 로 감쌀 경우)
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


def _normalize_verdict(raw: dict[str, Any]) -> dict[str, Any]:
    """심사관 응답 shape 을 다듬는다.

    판관이 필드를 빼먹거나 타입이 맞지 않아도 에이전트 루프가 깨지지 않도록
    안전한 기본값으로 보강한다.
    """
    violations_raw = raw.get("violations") or []
    violations: list[dict[str, str]] = []
    for v in violations_raw:
        if not isinstance(v, dict):
            continue
        violations.append(
            {
                "requirement": str(v.get("requirement", "")),
                "card": str(v.get("card", "")),
                "reason": str(v.get("reason", "")),
            }
        )

    passed = raw.get("passed")
    if not isinstance(passed, bool):
        passed = len(violations) == 0

    verdict = str(raw.get("verdict") or ("모든 요구사항 충족" if passed else "위반 있음"))

    return {
        "passed": passed,
        "violations": violations,
        "verdict": verdict,
    }


def _build_alert_block(
    verdict: str,
    violations: list[dict[str, str]],
    *,
    passed: bool,
    title_override: str | None = None,
) -> dict[str, Any]:
    """FE 에 렌더할 alert_card block 을 만든다.

    runner 가 tool 결과의 `emit_block` 을 감지하면 이 block 을 그대로 FE 로
    yield 한다. LLM 을 거치지 않으므로 프롬프트 의존 없이 항상 일관된 UI 가 뜬다.

    - passed=True → success 톤 "응답 평가 통과"
    - passed=False → warning 톤 "사용자 요구사항 위반 감지"
    - title_override 가 있으면 제목만 교체 (환각 감지 케이스 등).
    """
    if passed:
        return {
            "type": "alert_card",
            "severity": "success",
            "title": title_override or "응답 평가 통과",
            "summary": verdict,
            "items": [],
        }
    return {
        "type": "alert_card",
        "severity": "warning",
        "title": title_override or "사용자 요구사항 위반 감지",
        "summary": verdict,
        "items": [
            {
                "requirement": v["requirement"],
                "card": v["card"],
                "reason": v["reason"],
            }
            for v in violations
        ],
    }
