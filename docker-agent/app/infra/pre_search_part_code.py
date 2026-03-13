import re
import unicodedata
from typing import Iterable


DEFAULT_PART_CODE_PATTERNS: tuple[str, ...] = (
    r"\b[A-Za-z]{2,5}[- ]?\d{3,8}\b",
)


def _normalize_text(value: str | None) -> str:
    lowered = (value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


def compile_part_code_patterns(raw_patterns: Iterable[str] | None) -> tuple[re.Pattern[str], ...]:
    pattern_sources = list(raw_patterns or DEFAULT_PART_CODE_PATTERNS)
    compiled: list[re.Pattern[str]] = []
    seen: set[str] = set()

    for raw_pattern in pattern_sources:
        pattern = str(raw_pattern or "").strip()
        if not pattern:
            continue
        python_pattern = pattern.replace(r"\y", r"\b")
        if python_pattern in seen:
            continue
        compiled.append(re.compile(python_pattern, re.IGNORECASE))
        seen.add(python_pattern)

    if compiled:
        return tuple(compiled)
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in DEFAULT_PART_CODE_PATTERNS)


def normalize_part_code_candidate(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = re.sub(r"\s+", "-", text).strip("-").upper()
    if not normalized:
        return None
    return normalized


def matches_part_code_patterns(value: str, compiled_patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.fullmatch(value) for pattern in compiled_patterns)


def is_valid_part_code_candidate(
    value: str | None,
    *,
    compiled_patterns: tuple[re.Pattern[str], ...],
    vehicle_brand: str | None = None,
    vehicle_model: str | None = None,
    vehicle_year: int | None = None,
) -> bool:
    normalized_value = normalize_part_code_candidate(value)
    if not normalized_value:
        return False
    if not matches_part_code_patterns(normalized_value, compiled_patterns):
        return False

    match = re.fullmatch(r"([A-Z]{2,5})-?(\d{3,8})", normalized_value)
    if not match:
        return False

    prefix = match.group(1).lower()
    numeric_text = match.group(2)
    if vehicle_year is None or numeric_text != str(vehicle_year):
        return True

    comparable_tokens: set[str] = set()
    for raw_value in (vehicle_brand, vehicle_model):
        normalized_text = _normalize_text(raw_value)
        if not normalized_text:
            continue
        comparable_tokens.update(re.findall(r"[a-z0-9]+", normalized_text))
        collapsed = re.sub(r"[^a-z0-9]", "", normalized_text)
        if collapsed:
            comparable_tokens.add(collapsed)

    return prefix not in comparable_tokens
