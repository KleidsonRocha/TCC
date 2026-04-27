import re
import unicodedata


def normalize_pre_search_text(value: str | None) -> str:
    lowered = (value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", no_accents)
