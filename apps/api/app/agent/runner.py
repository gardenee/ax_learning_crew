"""에이전트 러너 — Claude SDK tool_use loop (streaming).

이 파일이 에이전트의 심장입니다.

while 루프 안에서 Claude API를 streaming으로 호출하고, stop_reason에 따라:
- tool_use  → tool 실행 → 결과를 messages에 추가 → 다시 호출
- end_turn  → 루프 종료
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Iterator
from uuid import UUID

from app.agent.block_stream_parser import BlockStreamParser
from app.agent.system_prompt import BASE_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.agent.tools_registry import TOOL_DEFINITIONS, execute_tool
from app.core.config import settings
from app.core.llm_client import get_client

logger = logging.getLogger(__name__)

# 일부 모델이 native tool_use 대신 텍스트 안에 XML 형 tool 호출 ("<function_calls><invoke...>")
# 을 흘리는 경우가 있다. 사용자 화면 노출 + 다음 턴 history 오염 양쪽 다 막기 위해 server 단에서 제거.
_XML_TOOL_LEAK_RE = re.compile(r"<function_calls\b[^>]*>.*?</function_calls\s*>\s*", re.DOTALL)


def _strip_tool_call_xml(text: str) -> str:
    return _XML_TOOL_LEAK_RE.sub("", text).strip()


@dataclass
class AgentSession:
    """에이전트 세션. 추천 흐름 동안 유지된다."""

    session_id: UUID
    participant_ids: list[UUID] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    tool_calls_log: list[dict] = field(default_factory=list)
    known_place_ids: set[str] = field(default_factory=set)


def run_agent_stream(session: AgentSession, user_input: dict) -> Iterator[dict]:
    """에이전트 루프를 실행하며 이벤트를 스트리밍으로 yield한다."""
    client = get_client()

    flags = user_input.get("session_flags") or {}
    if not flags.get("remember_history", True):
        session.messages = []

    self_check_enabled = flags.get("self_check", True)
    gen_ui_enabled = flags.get("gen_ui", True)
    system_prompt = SYSTEM_PROMPT if self_check_enabled else BASE_SYSTEM_PROMPT

    tool_definitions = _filter_tools_by_flags(TOOL_DEFINITIONS, flags, self_check_enabled)
    allowed_tool_names = {t["name"] for t in tool_definitions}

    session.messages.append({
        "role": "user",
        "content": _format_user_input(user_input),
    })

    for turn in range(settings.max_tool_turns):
        logger.info(f"Agent turn {turn + 1}/{settings.max_tool_turns}")

        final = _call_llm(client, session.messages, system_prompt, tool_definitions)

        # text 를 stop_reason 에 따라 다르게 방출:
        # - tool_use → reasoning_*
        # - end_turn (gen_ui ON)  → BlockStreamParser 로 JSONL/text 자동 분기
        # - end_turn (gen_ui OFF) → JSONL 파싱 안 하고 통째 message 한 덩어리로 회수
        #                            (세션 1~4 는 plain text 만 — LLM 이 block 을 흉내내도 텍스트로 본다)
        yield from _emit_text_events(final, gen_ui_enabled=gen_ui_enabled)

        # assistant 메시지를 히스토리에 기록
        session.messages.append({
            "role": "assistant",
            "content": [_content_block_to_dict(b) for b in final.content],
        })

        if final.stop_reason == "tool_use":
            tool_results = []
            ask_user_blocks: list[dict] | None = None

            for block in final.content:
                if block.type != "tool_use":
                    continue

                logger.info(f"Tool call: {block.name}")
                blocked = block.name not in allowed_tool_names

                # 차단된 tool 은 UI 에 호출 표시를 띄우지 않는다 — 토글 OFF 의 의도를 그대로 보이기 위해.
                # (단 history 에는 tool_use + error tool_result 가 그대로 들어가 다음 턴 LLM 이 인지.)
                if not blocked:
                    yield {
                        "type": "tool_status",
                        "tool": block.name,
                        "state": "start",
                        "input": block.input,
                    }

                if blocked:
                    logger.warning(
                        "blocked tool_use %s — not in allowed set for this request", block.name
                    )
                    result = {
                        "error": f"Tool {block.name!r} is disabled for this request.",
                        "tool": block.name,
                    }
                else:
                    result = execute_tool(block.name, block.input, session=session)

                session.tool_calls_log.append({
                    "tool": block.name,
                    "input": block.input,
                    "output_preview": str(result)[:200],
                    "blocked": blocked,
                })

                # 세션 6: search_restaurants 결과의 restaurant_id 를 세션에 누적.
                # "LLM 이 지어낸 식당" 을 rule-based 로 걸러낸다.
                if block.name == "search_restaurants" and isinstance(result, dict):
                    for cand in result.get("candidates") or []:
                        pid = cand.get("restaurant_id") if isinstance(cand, dict) else None
                        if isinstance(pid, str) and pid:
                            session.known_place_ids.add(pid)

                if not blocked:
                    yield {
                        "type": "tool_status",
                        "tool": block.name,
                        "state": "done",
                        "result": result,
                    }

                # 세션 5: ask_user 는 input block 묶음을 반환하고 루프를 끊는다.
                if (
                    block.name == "ask_user"
                    and isinstance(result, dict)
                    and result.get("should_break_loop")
                ):
                    blocks = result.get("emit_blocks")
                    if isinstance(blocks, list):
                        ask_user_blocks = [b for b in blocks if isinstance(b, dict)]

                if isinstance(result, dict) and isinstance(result.get("emit_block"), dict):
                    yield result["emit_block"]

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            session.messages.append({
                "role": "user",
                "content": tool_results,
            })

            if ask_user_blocks is not None:
                for b in ask_user_blocks:
                    yield b
                return

        elif final.stop_reason == "end_turn":
            return

        else:
            logger.warning(f"Unexpected stop_reason: {final.stop_reason}")
            return

    # max turns 초과 — fallback 메시지
    fallback_id = f"m_{uuid.uuid4().hex[:8]}"
    yield {"type": "message_start", "id": fallback_id}
    yield {
        "type": "message_delta",
        "id": fallback_id,
        "text": "추천을 생성하는 데 시간이 너무 오래 걸렸어요. 다시 시도해주세요.",
    }
    yield {"type": "message_end", "id": fallback_id}


# flag 이름 → 꺼질 때 제외할 tool 이름 집합.
_TOOL_GROUPS: dict[str, frozenset[str]] = {
    "tool_memory":   frozenset({"get_user_memory", "update_user_memory"}),
    "tool_search":   frozenset({"search_menus", "search_restaurants"}),
    "tool_weather":  frozenset({"get_weather"}),
    "tool_landmark": frozenset({"get_landmark"}),
    "tool_travel":   frozenset({"estimate_travel_time"}),
    # ask_user 는 gen_ui 의 sub-feature — 별도 토글 없이 gen_ui ON/OFF 를 따라간다.
    # `_filter_tools_by_flags` 에서 gen_ui OFF 면 ask_user 자동 제외.
}


def _filter_tools_by_flags(
    definitions: list[dict], flags: dict, self_check_enabled: bool
) -> list[dict]:
    """flags 에 맞춰 TOOL_DEFINITIONS 에서 비활성 tool 을 제거한다.

    LLM 입장에서 tool 이 아예 존재하지 않는 상태가 되므로 hallucinated 호출도
    발생하지 않는다.

    의존 관계: `ask_user` 는 input block (form) 을 emit 하므로 `gen_ui` OFF 면
    의미 없음 — `gen_ui` 가 master, `tool_ask_user` 는 sub. gen_ui OFF 면 ask_user
    도 자동 제외.
    """
    excluded: set[str] = set()
    if not self_check_enabled:
        excluded.add("evaluate_response")
    for flag_key, tool_names in _TOOL_GROUPS.items():
        if not flags.get(flag_key, True):
            excluded |= tool_names
    # ask_user 는 gen_ui 따라감 — gen_ui ON 이면 자동 활성, OFF 면 차단.
    if not flags.get("gen_ui", True):
        excluded.add("ask_user")
    return [t for t in definitions if t.get("name") not in excluded]


def _call_llm(client, messages: list[dict], system_prompt: str, tool_definitions: list[dict]):
    """Claude API를 호출하고 final_response 를 반환한다.

    stream() / create() 둘 다 지원하지만 이벤트 변환은 `_emit_text_events`
    에서 stop_reason 과 final.content 를 보고 한다
    """
    kwargs = dict(
        model=settings.model_id,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )
    if tool_definitions:
        kwargs["tools"] = tool_definitions

    if hasattr(client.messages, "stream"):
        with client.messages.stream(**kwargs) as stream:
            for _ in stream:
                pass
            return stream.get_final_message()

    return client.messages.create(**kwargs)


def _emit_text_events(final, *, gen_ui_enabled: bool = True) -> Iterator[dict]:
    """final.content 의 text block 들을 stop_reason 에 따라 이벤트로 변환."""
    text = "".join(
        b.text for b in final.content if b.type == "text" and b.text
    )
    text = _strip_tool_call_xml(text)
    if not text.strip():
        return

    if final.stop_reason == "tool_use":
        rid = f"r_{uuid.uuid4().hex[:8]}"
        yield {"type": "reasoning_start", "id": rid}
        yield {"type": "reasoning_delta", "id": rid, "text": text}
        yield {"type": "reasoning_end", "id": rid}
        return

    if not gen_ui_enabled:
        mid = f"m_{uuid.uuid4().hex[:8]}"
        yield {"type": "message_start", "id": mid}
        yield {"type": "message_delta", "id": mid, "text": text}
        yield {"type": "message_end", "id": mid}
        return

    parser = BlockStreamParser()
    yield from parser.feed(text)
    yield from parser.finalize()


def _format_user_input(user_input: dict) -> str:
    """사용자 입력을 에이전트가 이해할 수 있는 텍스트로 변환한다."""
    parts = []

    if user_input.get("user_message"):
        parts.append(user_input["user_message"])

    if user_input.get("form_answers"):
        parts.append(f"[폼 응답] {json.dumps(user_input['form_answers'], ensure_ascii=False)}")

    if user_input.get("constraints"):
        parts.append(f"[조건] {json.dumps(user_input['constraints'], ensure_ascii=False)}")

    if user_input.get("participant_ids"):
        parts.append(f"[참가자] {', '.join(user_input['participant_ids'])}")

    return "\n".join(parts) if parts else "점심 추천해줘"


def _content_block_to_dict(block) -> dict:
    """Claude API content block을 직렬화 가능한 dict로 변환한다."""
    if block.type == "text":
        return {"type": "text", "text": _strip_tool_call_xml(block.text)}
    if block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    return {"type": block.type}
