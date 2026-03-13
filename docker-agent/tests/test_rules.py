import logging

import pytest

from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.infra.tools_mock import MockTools
from app.config import Settings


def _catalog_fixture() -> PreSearchCatalog:
    return PreSearchCatalog(
        part_patterns=[
            ("filtro de oleo", ("filtro de oleo", "filtro oleo")),
            ("filtro", ("filtro",)),
            ("coxim", ("coxim",)),
            ("radiador", ("radiador",)),
            ("bandejas", ("bandejas",)),
        ],
        brand_aliases={"Ford": ("ford",)},
        model_aliases={"EcoSport": ("ecosport",), "Gol": ("gol",), "2008": ("2008",)},
        invalid_slot_tokens={"nao"},
        generic_ambiguous_parts={"filtro"},
        needs_side=set(),
        needs_position=set(),
        needs_axle={"bandejas"},
        needs_engine={"radiador"},
        needs_variant=set(),
        engine_by_model={"ecosport": ["1.6", "2.0", "Nao sei"]},
    )


def _validator_settings() -> Settings:
    return Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        CATALOG_DB_ENABLED=False,
        LLM_BASE_URL="http://127.0.0.1:1",
        LLM_MODEL="qwen2.5:7b",
        LLM_TIMEOUT_MS=1000,
        LLM_LOG_RAW_RESPONSE=False,
    )


def _validator(*, catalog: PreSearchCatalog | None = None) -> LLMPreSearchValidator:
    return LLMPreSearchValidator(
        settings=_validator_settings(),
        logger=logging.getLogger("test"),
        catalog=catalog or _catalog_fixture(),
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


def test_dictionary_extractor_extracts_axle_when_eixo_is_present() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero coxim do eixo dianteiro da ecosport"
    )
    assert result.part_query == "coxim"
    assert result.axle == "front"


def test_dictionary_extractor_prefers_text_model_over_numeric_year_like_model() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "ecosport 2008"
    )
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_extracts_explicit_part_code() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero o codigo AB-1234 para ecosport"
    )
    assert result.part_code == "AB-1234"


def test_dictionary_extractor_rejects_model_year_as_part_code() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "radiador gol 2010"
    )
    assert result.part_code is None


def test_llm_validator_ignores_hallucinated_part_code_from_llm() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"radiador","part_code":"GOL-2010",'
                    '"vehicle_model":"Gol","vehicle_year":2010},"missing_fields":["engine"],'
                    '"next_question":{"type":"request_info","key":"engine","prompt":"Qual a motorizacao?"},'
                    '"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("radiador gol 2010")

    assert result.decision == "ask"
    assert result.criteria.part_code is None
    assert "engine" in result.missing_fields


def test_llm_validator_promotes_explicit_part_code_to_search() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{},"missing_fields":["part_query"],'
                    '"next_question":{"type":"request_info","key":"part_query","prompt":"Qual peca voce precisa?"},'
                    '"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("AB-1234")

    assert result.decision == "search"
    assert result.criteria.part_code == "AB-1234"
    assert result.missing_fields == []


def test_llm_validator_generates_default_engine_question_when_llm_omits_it() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"radiador","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":["engine"],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("radiador gol 2010")

    assert result.decision == "ask"
    assert result.missing_fields == ["engine"]
    assert result.next_question is not None
    assert result.next_question.key == "engine"
    assert result.next_question.prompt == "Qual a motorizacao do veiculo?"
    assert result.next_question.options == ["1.0", "1.6", "2.0", "Nao sei"]


def test_llm_validator_raw_fallback_keeps_ask_for_missing_engine() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": '{"decision":"ask"'
            }
        },
        "/api/chat",
    )

    result = validator.validate("radiador gol 2010")

    assert result.decision == "ask"
    assert result.missing_fields == ["engine"]
    assert result.next_question is not None
    assert result.next_question.key == "engine"


def test_llm_validator_asks_for_vehicle_year_on_ambiguous_generic_part() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"filtro","vehicle_model":"Gol"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("filtro gol")

    assert result.decision == "ask"
    assert result.missing_fields == ["vehicle_year"]
    assert result.next_question is not None
    assert result.next_question.key == "vehicle_year"
    assert result.next_question.prompt == "Qual o ano do veiculo?"


def test_llm_validator_position_satisfies_axle_requirement() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"bandejas","vehicle_model":"Ecosport",'
                    '"vehicle_year":2008,"position":"dianteira"},"missing_fields":[],'
                    '"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("bandejas ecosport 2008 dianteira")

    assert result.decision == "search"
    assert result.missing_fields == []
    assert result.criteria.position == "front"
    assert result.criteria.axle is None


def test_llm_validator_asks_when_score_is_below_minimum_even_without_rule_missing() -> None:
    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns,
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases=_catalog_fixture().model_aliases,
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side=_catalog_fixture().needs_side,
        needs_position=_catalog_fixture().needs_position,
        needs_axle=_catalog_fixture().needs_axle,
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
        min_score_to_search=90,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"coxim","vehicle_model":"Ecosport"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("coxim ecosport")

    assert result.decision == "ask"
    assert result.next_question is not None
    assert result.next_question.key == "vehicle_year"
    assert "vehicle_year" in result.missing_fields
