"""에이전트 system prompt.

런타임은 세션 6 프롬프트(최종 상태)를 그대로 사용한다. 세션 1~5 프롬프트는
같은 폴더에 파일로 보존되며, 각 파일은 **그 세션 시점의 전문(全文)** 으로
독립 작성된다(BASE import chain 없음). 프롬프트 diff 비교는 `session_NN.py`
파일을 직접 비교한다.
"""

from __future__ import annotations

from app.agent.prompts.session_06 import BASE_SYSTEM_PROMPT, EVAL_RULES, SYSTEM_PROMPT

__all__ = ["BASE_SYSTEM_PROMPT", "EVAL_RULES", "SYSTEM_PROMPT"]
