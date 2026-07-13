import re
import unicodedata
from typing import Iterable


_PART_CODE_COMPONENTS = re.compile(r"^([A-Z]{2,5})-?(\d{3,8})$")
_EXPLICIT_CODE_MARKER_SUFFIX = re.compile(
    r"(?:\b(?:codigo|cod|referencia|ref|sku)\b\.?"
    r"(?:\s+(?:da|do|de)\s+peca)?\s*[:#-]?\s*)$",
    re.IGNORECASE,
)


def normalize_part_code_candidate(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = re.sub(r"\s+", "-", text).strip("-").upper()
    if not normalized:
        return None
    return normalized


def has_literal_part_code_evidence(
    value: str | None,
    *,
    message_text: str,
    last_messages: Iterable[dict[str, object]] | None = None,
) -> bool:
    normalized_value = normalize_part_code_candidate(value)
    if not normalized_value:
        return False

    texts = [str(message_text or "")]
    for message in last_messages or []:
        role = str(message.get("role", "")).strip().lower()
        if role and role != "user":
            continue
        texts.append(str(message.get("text", "") or ""))

    return any(
        _text_contains_literal_part_code(normalized_value, text)
        for text in texts
        if str(text or "").strip()
    )


def _text_contains_literal_part_code(normalized_value: str, text: str) -> bool:
    source = str(text or "")
    components = _PART_CODE_COMPONENTS.fullmatch(normalized_value)
    if components is None:
        return bool(
            re.search(
                rf"(?<![A-Za-z0-9]){re.escape(normalized_value)}(?![A-Za-z0-9])",
                source,
                re.IGNORECASE,
            )
        )

    prefix, digits = components.groups()
    token_start = rf"(?<![A-Za-z0-9]){re.escape(prefix)}"
    token_end = rf"{re.escape(digits)}(?![A-Za-z0-9])"

    if re.search(rf"{token_start}\s*-\s*{token_end}", source, re.IGNORECASE):
        return True
    if re.search(rf"{token_start}{token_end}", source, re.IGNORECASE):
        return True

    stripped_source = source.strip().strip(".,;:!?()[]{}\"'")
    if re.fullmatch(
        rf"{re.escape(prefix)}\s+{re.escape(digits)}",
        stripped_source,
        re.IGNORECASE,
    ):
        return True

    for match in re.finditer(
        rf"{token_start}\s+{token_end}",
        source,
        re.IGNORECASE,
    ):
        prefix_context = _normalize_evidence_text(
            source[max(0, match.start() - 80) : match.start()]
        )
        if _EXPLICIT_CODE_MARKER_SUFFIX.search(prefix_context):
            return True

    return False


def _normalize_evidence_text(value: str) -> str:
    lowered = str(value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", no_accents)
