from typing import Any, Literal

from app.core.domain.models import HandoffInfo

ConversationStage = Literal["more_info", "mostrar_produtos", "transfer_to_human", "fallback"]


def response_stage(*, handoff: HandoffInfo, actions: list[dict[str, Any]]) -> ConversationStage:
    if handoff.required:
        return "transfer_to_human"
    if any(isinstance(action, dict) and action.get("type") == "request_info" for action in actions):
        return "more_info"
    if any(isinstance(action, dict) and action.get("type") == "show_items" for action in actions):
        return "mostrar_produtos"
    return "fallback"


def presentation_items(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict) or action.get("type") != "show_items":
            continue
        action_items = action.get("items")
        if isinstance(action_items, list):
            items.extend(item for item in action_items if isinstance(item, dict))
    return items


def presentation_text(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        code = str(item.get("item_id") or "").strip()
        title = str(item.get("title") or "").strip()
        description = " - ".join(part for part in (code, title) if part)
        if description:
            lines.append(f"{index}. {description}")
    return "\n".join(lines)
