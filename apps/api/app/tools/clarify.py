"""ask_user tool — 사용자에게 추가 정보를 묻기 위한 input block 들을 emit.

다른 tool 은 "외부 데이터를 가져와 결과 반환" 이지만 `ask_user` 는 결과가
**사용자가 채워야 하는 입력 UI** 다. tool 이 흐름을 제어한다.

runner 는 반환값의 `should_break_loop=True` 를 보고 `emit_blocks` 를 프런트에
순차 yield 한 뒤 루프를 끝낸다. 사용자가 폼을 제출하면 같은 `session_id` 로
재호출되어 대화가 이어진다.

emit 순서:
  1. message           — 왜 물어보는지 한 줄 안내
  2. <input> × N       — LLM 이 요청한 fields (같은 form_id 로 묶임)
  3. submit_button     — form_id 묶음을 한 번에 제출

LLM 이 보내는 `fields` 는 완벽하지 않을 수 있어 검증한다:
- `name`/`label` 누락 필드 → 제거
- 알 수 없는 `kind` → `text` fallback
- `value` 없는 option → 제거
- 전부 무효하면 → 기본 text 필드 하나 삽입

──────────────────────────────────────────────────────────────
완성본. `tool_ask_user` 토글로 껐다 켤 수 있습니다.
도전 과제: 새로운 input block 타입(예: slider, date_input)을 추가해 보세요.
FE 쪽 렌더러 (`apps/web/src/components/blocks/`) 도 같이 건드려야 합니다.
──────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from uuid import uuid4

# LLM 의 kind 값 → FE block type 매핑. multi-select 는 chips_input(multiple=True) 로 접힌다.
_KIND_TO_BLOCK = {
    "text": ("text_input", {}),
    "number": ("number_input", {}),
    "select": ("select_input", {}),
    "chips": ("chips_input", {"multiple": False}),
    "multi-select": ("chips_input", {"multiple": True}),
}


def handle(reason: str, fields: list[dict]) -> dict:
    """LLM 이 보낸 fields 를 검증해 input block 배열을 만든다."""
    form_id = f"clarify-{uuid4().hex[:8]}"
    validated = _validate_fields(fields)

    blocks: list[dict] = []
    if reason:
        blocks.append({
            "type": "message",
            "id": f"ask-{uuid4().hex[:8]}",
            "text": reason,
        })

    for field in validated:
        blocks.append(_field_to_block(form_id, field))

    blocks.append({
        "type": "submit_button",
        "form_id": form_id,
        "label": "확인",
    })

    return {
        "emit_blocks": blocks,
        "form_id": form_id,
        "should_break_loop": True,
    }


def _field_to_block(form_id: str, field: dict) -> dict:
    """검증된 field dict → FE input block."""
    kind = field["kind"]
    block_type, extra = _KIND_TO_BLOCK[kind]

    block: dict = {
        "type": block_type,
        "form_id": form_id,
        "name": field["name"],
        "label": field["label"],
        **extra,
    }
    if field.get("required"):
        block["required"] = True
    if field.get("helper_text"):
        block["helper_text"] = field["helper_text"]
    if field.get("placeholder"):
        block["placeholder"] = field["placeholder"]
    for key in ("min", "max", "unit", "default_value"):
        if key in field:
            block[key] = field[key]
    if field.get("options"):
        block["options"] = field["options"]
    return block


def _validate_fields(fields: list[dict]) -> list[dict]:
    validated: list[dict] = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        label = field.get("label")
        if not name or not label:
            continue

        kind = field.get("kind") or "text"
        if kind not in _KIND_TO_BLOCK:
            kind = "text"

        entry: dict = {"kind": kind, "name": name, "label": label}
        for key in ("required", "helper_text", "placeholder", "min", "max", "unit", "default_value"):
            if key in field:
                entry[key] = field[key]

        options = _validate_options(field.get("options"))
        if options:
            entry["options"] = options

        validated.append(entry)

    if not validated:
        validated.append(
            {
                "kind": "text",
                "name": "user_input",
                "label": "원하는 조건을 알려주세요",
            }
        )
    return validated


def _validate_options(options) -> list[dict]:
    if not isinstance(options, list):
        return []
    clean: list[dict] = []
    for opt in options:
        if not isinstance(opt, dict):
            continue
        value = opt.get("value")
        label = opt.get("label") or value
        if value is None:
            continue
        clean.append({"label": str(label), "value": str(value)})
    return clean
