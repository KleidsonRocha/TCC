import re

from app.core.domain.errors import InvalidMessageError


def normalize_branch_id(branch_id: int | str | None, default_branch_id: int) -> tuple[int, bool]:
    if branch_id is None:
        return default_branch_id, True
    try:
        normalized = int(branch_id)
    except (TypeError, ValueError):
        return default_branch_id, True
    if normalized <= 0:
        return default_branch_id, True
    return normalized, False


def validate_text(text: str) -> None:
    if not text or not text.strip():
        raise InvalidMessageError("Campo 'text' nao pode ser vazio.")


def normalize_source(source: str | None) -> str:
    if source is None:
        return "generic"
    normalized = source.strip().lower()
    if not normalized:
        return "generic"
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9._-]", "", normalized)
    return normalized or "generic"


def build_internal_conversation_id(source: str, conversation_id: str) -> str:
    cleaned_conversation_id = conversation_id.strip()
    prefix = f"{source}:"
    if cleaned_conversation_id.lower().startswith(prefix):
        return cleaned_conversation_id
    return f"{source}:{cleaned_conversation_id}"
