"""LLM 출력 스트림을 Generative UI block 이벤트로 파싱한다.

세션 5 (Generative UI) 의 핵심 파서.

## 응답 포맷 두 갈래

에이전트 루프가 Claude API 로부터 받는 text 는 세션별 프롬프트에 따라 두 형태 중 하나다.

1. **JSONL (세션 5)** — 각 줄이 하나의 UI block.
2. **plain text (세션 1~4)** — 자연어 문장.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Iterator

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*")


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text)


class BlockStreamParser:
    def __init__(self) -> None:
        self._buffer: str = ""
        self._mode: str | None = None  # None | "jsonl" | "text"
        self._text_id: str | None = None

    def feed(self, delta: str) -> Iterator[dict]:
        if not delta:
            return
        self._buffer += delta

        if self._mode is None:
            yield from self._decide_mode()

        if self._mode == "text":
            yield from self._flush_text()
        elif self._mode == "jsonl":
            yield from self._flush_jsonl()

    def finalize(self) -> Iterator[dict]:
        if self._mode is None and self._buffer.strip():
            self._mode = "text"
            self._text_id = f"m_{uuid.uuid4().hex[:8]}"
            yield {"type": "message_start", "id": self._text_id}

        if self._mode == "text":
            yield from self._flush_text()
            if self._text_id:
                yield {"type": "message_end", "id": self._text_id}
                self._text_id = None
            return

        if self._mode == "jsonl":
            leftover = _strip_fences(self._buffer).strip()
            self._buffer = ""
            if not leftover:
                return
            try:
                yield json.loads(leftover)
            except json.JSONDecodeError:
                logger.warning("JSONL finalize parse failed: %r", leftover[:200])
                yield _fallback_message(leftover)

    # --- internal ---

    def _decide_mode(self) -> Iterator[dict]:
        stripped = self._buffer.lstrip()
        if not stripped:
            return
        if stripped[0] == "{":
            self._mode = "jsonl"
            self._buffer = stripped
            return

        # preamble recovery — LLM 이 JSONL 앞에 "최종 응답을 구성하겠습니다" 같은
        # 설명을 붙이거나 ```json ... ``` 으로 감싸는 경우를 방어한다.
        # buffer 안에서 line-start `{` 를 찾아 그 앞은 단일 message 로 방출하고,
        # 나머지를 jsonl 모드로 회수한다. preamble 에 섞인 코드펜스 마커는 제거.
        jsonl_start = self._buffer.find("\n{")
        if jsonl_start >= 0:
            preamble = _strip_fences(self._buffer[:jsonl_start]).strip()
            if preamble:
                logger.warning(
                    "JSONL preamble detected; recovering as message block: %r",
                    preamble[:120],
                )
                yield {
                    "type": "message",
                    "id": f"m_{uuid.uuid4().hex[:8]}",
                    "text": preamble,
                }
            self._mode = "jsonl"
            self._buffer = self._buffer[jsonl_start + 1 :]
            return

        self._mode = "text"
        self._text_id = f"m_{uuid.uuid4().hex[:8]}"
        yield {"type": "message_start", "id": self._text_id}

    def _flush_text(self) -> Iterator[dict]:
        if not self._buffer or not self._text_id:
            return
        yield {"type": "message_delta", "id": self._text_id, "text": self._buffer}
        self._buffer = ""

    def _flush_jsonl(self) -> Iterator[dict]:
        decoder = json.JSONDecoder()
        while True:
            stripped_buf = self._buffer.lstrip()
            if not stripped_buf:
                self._buffer = ""
                return
            if stripped_buf != self._buffer:
                self._buffer = stripped_buf
            try:
                block, end_idx = decoder.raw_decode(self._buffer)
            except json.JSONDecodeError:
                return
            self._buffer = self._buffer[end_idx:]
            self._buffer = self._buffer.lstrip()
            if isinstance(block, dict) and block.get("type"):
                yield block
            else:
                yield _fallback_message(json.dumps(block, ensure_ascii=False))


def _fallback_message(text: str) -> dict:
    """파싱 실패 시 사용자에게 보여줄 안전한 message block."""
    return {
        "type": "message",
        "id": f"m_{uuid.uuid4().hex[:8]}",
        "text": text,
    }
