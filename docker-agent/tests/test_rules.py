import pytest

from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.infra.tools_mock import MockTools


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


def test_mock_tool_returns_empty_for_unknown_query() -> None:
    items = MockTools().search_parts("item inexistente", branch_id=1)
    assert items == []
