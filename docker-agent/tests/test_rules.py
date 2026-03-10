import pytest

from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.tools_mock import MockTools


def _catalog_fixture() -> PreSearchCatalog:
    return PreSearchCatalog(
        part_patterns=[
            ("filtro de oleo", ("filtro de oleo", "filtro oleo")),
            ("coxim", ("coxim",)),
        ],
        brand_aliases={"Ford": ("ford",)},
        model_aliases={"EcoSport": ("ecosport",)},
        invalid_slot_tokens={"nao"},
        generic_ambiguous_parts={"filtro"},
        needs_side=set(),
        needs_position=set(),
        needs_engine=set(),
        engine_by_model={"ecosport": ["1.6", "2.0", "Nao sei"]},
    )


def test_validate_schema_version_accepts_v1() -> None:
    validate_schema_version("1.0")


def test_validate_schema_version_rejects_unknown_version() -> None:
    with pytest.raises(UnsupportedSchemaVersionError):
        validate_schema_version("2.0")


def test_validate_message_text_rejects_empty_text() -> None:
    with pytest.raises(InvalidMessageError):
        validate_message_text("   ")


def test_mock_tool_returns_two_items_for_bandeja() -> None:
    items = MockTools().search_parts("Preciso de bandeja da ecosport", branch_id=1)
    assert len(items) == 2


def test_mock_tool_returns_single_item_for_filtro_de_oleo() -> None:
    items = MockTools().search_parts("quero filtro de oleo", branch_id=1)
    assert len(items) == 1


def test_mock_tool_returns_single_item_for_coxim() -> None:
    items = MockTools().search_parts("coxim ecosport 2008", branch_id=1)
    assert len(items) == 1


def test_mock_tool_returns_empty_for_unknown_query() -> None:
    items = MockTools().search_parts("item inexistente", branch_id=1)
    assert items == []


def test_dictionary_extractor_extracts_part_model_and_year() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "Quero 2 unidade do filtro de oleo da ford ecosport 2008"
    )
    assert result.part_query == "filtro de oleo"
    assert result.vehicle_brand == "Ford"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_uses_last_messages_for_year() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "Quero filtro de oleo para ecosport",
        last_messages=[{"role": "user", "text": "2008"}],
    )
    assert result.part_query == "filtro de oleo"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_uses_previous_full_question_when_message_is_only_year() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "2008",
        last_messages=[
            {"role": "user", "text": "coxim ecosport"},
            {"role": "assistant", "text": "Qual o ano do veiculo?"},
        ],
    )
    assert result.part_query == "coxim"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008
