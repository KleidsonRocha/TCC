import pytest

from app.core.domain.errors import InvalidMessageError
from app.core.domain.rules import (
    build_internal_conversation_id,
    normalize_branch_id,
    normalize_source,
    validate_text,
)


def test_normalize_branch_uses_default_when_missing() -> None:
    value, corrected = normalize_branch_id(None, default_branch_id=1)
    assert value == 1
    assert corrected is True


@pytest.mark.parametrize("invalid_value", [0, -1, "abc"])
def test_normalize_branch_uses_default_when_invalid(invalid_value) -> None:
    value, corrected = normalize_branch_id(invalid_value, default_branch_id=1)
    assert value == 1
    assert corrected is True


def test_validate_text_rejects_empty_or_whitespace() -> None:
    with pytest.raises(InvalidMessageError):
        validate_text("   ")


def test_normalize_source_defaults_to_generic() -> None:
    assert normalize_source(None) == "generic"
    assert normalize_source("   ") == "generic"


def test_normalize_source_sanitizes_value() -> None:
    assert normalize_source("Whats App!") == "whats-app"


def test_build_internal_conversation_id_namespaces_source() -> None:
    assert build_internal_conversation_id("webchat", "conv-1") == "webchat:conv-1"


def test_build_internal_conversation_id_keeps_existing_prefix() -> None:
    assert build_internal_conversation_id("webchat", "webchat:conv-1") == "webchat:conv-1"
