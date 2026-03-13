import json
from typing import Any

from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria


def normalize_context_messages(raw_messages: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw_messages or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user")).strip() or "user"
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized.append({"role": role, "text": text})
    return normalized


def build_fine_tuning_user_payload(
    *,
    message_text: str,
    last_messages: list[dict[str, Any]] | None,
    dictionary_seed_criteria: dict[str, Any],
    score_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "message_text": str(message_text or "").strip(),
        "last_messages": normalize_context_messages(last_messages),
        "dictionary_seed_criteria": dict(dictionary_seed_criteria or {}),
        "score_policy": dict(score_policy or {}),
    }


def build_fine_tuning_assistant_payload(
    *,
    decision: str,
    criteria: dict[str, Any] | None,
    missing_fields: list[str] | None,
    next_question: dict[str, Any] | None,
    confidence: float,
) -> dict[str, Any]:
    criteria_model = SearchCriteria.model_validate(criteria or {})
    next_question_model = (
        NextQuestion.model_validate(next_question)
        if next_question is not None
        else None
    )
    validation = PreSearchValidation.model_validate(
        {
            "decision": decision,
            "criteria": criteria_model.model_dump(exclude_none=True),
            "missing_fields": list(missing_fields or []),
            "next_question": (
                next_question_model.model_dump(exclude_none=True)
                if next_question_model is not None
                else None
            ),
            "confidence": confidence,
        }
    )
    return validation.model_dump(exclude_none=False)


def build_fine_tuning_messages_record(
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    assistant_payload: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": str(system_prompt or "").strip()},
            {"role": "user", "content": dumps_json(user_payload)},
            {"role": "assistant", "content": dumps_json(assistant_payload)},
        ],
        "metadata": dict(metadata or {}),
    }


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
