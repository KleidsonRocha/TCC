import re
import unicodedata


_FRONT_DIRECTION_PATTERN = re.compile(r"\b(diant|dianteir[oa])\b")
_REAR_DIRECTION_PATTERN = re.compile(r"\b(tras|traseir[oa])\b")


def normalize_pre_search_text(value: str | None) -> str:
    lowered = (value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


def canonicalize_longitudinal_direction(value: str | None) -> str | None:
    """Map grammatical variants to the canonical search values `front`/`rear`."""

    normalized = normalize_pre_search_text(value)
    if _FRONT_DIRECTION_PATTERN.search(normalized):
        return "front"
    if _REAR_DIRECTION_PATTERN.search(normalized):
        return "rear"
    return None


def longitudinal_direction_search_fragment(value: str | None) -> str | None:
    """Return the gender-neutral ERP fragment for a canonical direction."""

    return {"front": "dianteir", "rear": "traseir"}.get(value or "")
