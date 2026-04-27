from app.infra.pre_search_text import normalize_pre_search_text


def test_normalize_pre_search_text_lowercases_strips_accents_and_collapses_spaces() -> None:
    result = normalize_pre_search_text("  Fíltro   de   Óleo  ")

    assert result == "filtro de oleo"


def test_normalize_pre_search_text_handles_none() -> None:
    assert normalize_pre_search_text(None) == ""
