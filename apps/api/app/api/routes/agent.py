"""에이전트 API route — SSE streaming.

에이전트 루프가 생성하는 이벤트를 Server-Sent Events로 흘려보낸다.
FE는 fetch + ReadableStream으로 수신하여 채팅 UI를 갱신한다.

SSE 이벤트 스키마 (모든 이벤트 동일한 `data: {json}\\n\\n` 형식):
- {"type": "session",        "session_id": "..."}              # 스트림 시작 시 1회
- {"type": "message_start",  "id": "m_xxx"}
- {"type": "message_delta",  "id": "m_xxx", "text": "안녕"}
- {"type": "message_end",    "id": "m_xxx"}
- {"type": "reasoning_start","id": "r_xxx"}                     # tool_use 턴의 진행 해설
- {"type": "reasoning_delta","id": "r_xxx", "text": "..."}
- {"type": "reasoning_end",  "id": "r_xxx"}
- {"type": "tool_status",    "tool": "search_restaurants", "state": "start" | "done", "input"?: {...}}
- {"type": "done",           "debug_info": {...}}              # 스트림 종료 시 1회
- {"type": "error",          "message": "..."}                  # 예외 발생 시

세션 5 (Generative UI) 에서는 이 위에 atomic block 이벤트(recommendation_card 등)가 얹힌다.
"""

import json
import logging
import time
from typing import Iterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.block_stream_parser import BlockStreamParser
from app.agent.runner import AgentSession, run_agent_stream
from app.models.request_models import AgentRunRequest
from app.repositories.chat_messages import load_messages, save_messages
from app.repositories.chat_sessions import list_sessions, upsert_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

_sessions: dict[str, AgentSession] = {}


@router.post("/run")
def agent_run(req: AgentRunRequest):
    """에이전트 루프를 SSE로 스트리밍한다."""
    start = time.time()

    # 세션 조회 또는 생성
    # 1) in-memory 캐시 hit → 그대로
    # 2) session_id 주어졌지만 캐시 miss → Postgres(chat_messages) 에서 복원 시도
    # 3) 없으면 신규 세션
    if req.session_id and str(req.session_id) in _sessions:
        session = _sessions[str(req.session_id)]
    else:
        sid = req.session_id or uuid4()
        persisted = load_messages(sid) if req.session_id else []
        session = AgentSession(
            session_id=sid,
            participant_ids=req.participant_ids,
            constraints=req.constraints.model_dump() if req.constraints else {},
            messages=persisted,
        )
        _sessions[str(session.session_id)] = session

    if req.constraint_patch:
        session.constraints.update(req.constraint_patch)

    flags = req.session_flags.model_dump() if req.session_flags else {}
    remember_history = flags.get("remember_history", True)

    # 사이드바 목록용으로 DB에 세션 메타를 upsert
    if remember_history:
        upsert_session(
            session.session_id,
            title=(req.user_message or "").strip() or None,
        )

    user_input = {
        "user_message": req.user_message,
        "form_answers": req.form_answers,
        "constraints": session.constraints,
        "participant_ids": [str(uid) for uid in req.participant_ids],
        "session_flags": flags,
    }

    # 이번 호출에서 새로 쌓인 tool 호출만 debug_info에 싣기 위한 기준 인덱스
    tool_log_start = len(session.tool_calls_log)

    def sse() -> Iterator[str]:
        completed = False
        try:
            yield _sse({"type": "session", "session_id": str(session.session_id)})

            for event in run_agent_stream(session, user_input):
                yield _sse(event)

            # 스트림이 정상 종료된 시점에 대화 이력 스냅샷을 Postgres 에 저장한다.
            if remember_history:
                save_messages(session.session_id, session.messages)

            debug = {
                "tool_calls": [log["tool"] for log in session.tool_calls_log[tool_log_start:]],
                "latency_ms": int((time.time() - start) * 1000),
            }
            yield _sse({"type": "done", "debug_info": debug})
            completed = True

        except GeneratorExit:
            # 사용자가 정지 버튼을 눌렀거나 페이지를 벗어나 fetch 가 abort 된 경우 처리
            if not completed:
                session.messages = _prune_incomplete_tool_tail(session.messages)
                if remember_history:
                    try:
                        save_messages(
                            session.session_id,
                            session.messages,
                            status="aborted",
                        )
                    except Exception:  # noqa: BLE001
                        logger.exception("aborted snapshot save failed")
            raise

        except Exception as exc:  # noqa: BLE001
            logger.exception("agent stream failed")
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 방지
        },
    )


@router.get("/sessions")
def agent_sessions(limit: int = 30):
    """사이드바 최근 대화 목록."""
    return {"sessions": list_sessions(limit=limit)}


@router.get("/sessions/{session_id}")
def agent_session_detail(session_id: str):
    """세션 상세 — 대화 내역을 FE turn 포맷으로 복원한다.

    조회 순서:
    1. in-memory `_sessions` 캐시 hit → 그대로 사용
    2. miss → Postgres `chat_messages` 에서 복원
    3. 둘 다 없으면 빈 turns
    """
    session = _sessions.get(session_id)
    if session is not None:
        messages = session.messages
    else:
        from uuid import UUID

        try:
            messages = load_messages(UUID(session_id))
        except (ValueError, TypeError):
            messages = []

    return {
        "session_id": session_id,
        "turns": _messages_to_turns(messages),
    }


def _messages_to_turns(messages: list[dict]) -> list[dict]:
    """Claude messages → FE turn 배열."""
    turns: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "user":
            text = _extract_user_text(content)
            if text:
                turns.append({"kind": "user", "text": text})

        elif role == "assistant" and isinstance(content, list):
            has_tool_use = any(b.get("type") == "tool_use" for b in content)
            blocks: list[dict] = []
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    t = (block.get("text") or "").strip()
                    if not t:
                        continue
                    if has_tool_use:
                        blocks.append({
                            "type": "reasoning",
                            "id": f"r_{len(turns)}_{len(blocks)}",
                            "text": t,
                            "collapsed": True,
                        })
                    else:
                        blocks.extend(_parse_assistant_text(t))
                elif btype == "tool_use":
                    blocks.append({
                        "type": "tool_status",
                        "tool": block.get("name", ""),
                        "state": "done",
                        "input": block.get("input") or {},
                        "collapsed": True,
                    })
            if blocks:
                turns.append({"kind": "assistant", "blocks": blocks})

    return turns


def _parse_assistant_text(text: str) -> list[dict]:
    """assistant text 한 덩어리를 스트리밍 파서에 태워 FE block 배열로 복원한다.

    - JSONL 이면 atomic block 들이 그대로 yield 되고,
    - plain text 면 message_start/delta/end 이벤트가 오므로 하나의 message block 으로 모은다.
    """
    parser = BlockStreamParser()
    events = list(parser.feed(text)) + list(parser.finalize())

    blocks: list[dict] = []
    current_message: dict | None = None
    for event in events:
        etype = event.get("type")
        if etype == "message_start":
            current_message = {"type": "message", "text": "", "streaming": False}
            blocks.append(current_message)
        elif etype == "message_delta":
            if current_message is not None:
                current_message["text"] += event.get("text", "")
        elif etype == "message_end":
            if current_message is not None:
                current_message["text"] = current_message["text"].strip()
                if not current_message["text"]:
                    blocks.remove(current_message)
                current_message = None
        else:
            current_message = None
            block = {k: v for k, v in event.items()}
            if block.get("type") == "message" and not (block.get("text") or "").strip():
                continue
            blocks.append(block)
    return blocks


def _extract_user_text(content) -> str:
    """_format_user_input이 만든 문자열에서 사용자 발화만 추출한다."""
    if not isinstance(content, str):
        return ""
    lines = [line for line in content.split("\n") if line and not line.startswith("[")]
    return "\n".join(lines).strip()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _prune_incomplete_tool_tail(messages: list[dict]) -> list[dict]:
    """tail 의 assistant 메시지에 tool_use 가 있는데 짝이 될 tool_result 가 없다면 그 assistant 메시지를 제거한다."""
    if not messages:
        return messages
    last = messages[-1]
    if last.get("role") != "assistant":
        return messages
    content = last.get("content") or []
    has_tool_use = isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_use" for b in content
    )
    return messages[:-1] if has_tool_use else messages
