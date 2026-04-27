import logging

import pytest

from app.core.domain.models import ConversationState
from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.domain.pre_search import SearchCriteria
from app.infra.erp_search_tools_pg import resolve_search_tools
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.config import Settings


def _catalog_fixture() -> PreSearchCatalog:
    return PreSearchCatalog(
        part_patterns=[
            ("filtro de oleo", ("filtro de oleo", "filtro oleo")),
            ("filtro", ("filtro", "filtros")),
            ("batentes", ("batentes",)),
            ("coxim", ("coxim",)),
            ("radiador", ("radiador",)),
            ("bandejas", ("bandeja", "bandejas", "bandenja", "bandeija")),
            ("pastilha de freio", ("pastilha de freio", "pastilha freio", "pastilha", "pastilhas", "pastilhas de freio", "pstilhas")),
            ("disco de freio", ("disco de freio", "disco freio", "discos de freio")),
        ],
        brand_aliases={"Ford": ("ford",)},
        model_aliases={"EcoSport": ("ecosport",), "Gol": ("gol",), "2008": ("2008",)},
        invalid_slot_tokens={"nao"},
        generic_ambiguous_parts={"filtro"},
        needs_side={"bandejas"},
        needs_position={"pastilha de freio", "disco de freio"},
        needs_axle=set(),
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


def test_resolve_search_tools_requires_real_backend() -> None:
    settings = Settings(
        LOG_LEVEL="INFO",
        APP_ENV="test",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        ERP_DB_ENABLED=False,
    )

    with pytest.raises(RuntimeError):
        resolve_search_tools(settings=settings, logger=logging.getLogger("test"))


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


def test_dictionary_extractor_ignores_assistant_text_when_rebuilding_context() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "2008",
        last_messages=[
            {"role": "user", "text": "coxim ecosport"},
            {"role": "assistant", "text": "Talvez seja filtro focus 2011"},
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


def test_dictionary_extractor_fuzzy_matches_single_token_part_typo() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero cuxim da ecosport 2008"
    )
    assert result.part_query == "coxim"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_fuzzy_matches_transposed_single_token_typo() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero coxmi da ecosport 2008"
    )
    assert result.part_query == "coxim"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_fuzzy_matches_multiword_part_typo() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso do filtro de olei do gol 2015"
    )
    assert result.part_query == "filtro de oleo"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2015


def test_dictionary_extractor_canonicalizes_plural_part_alias() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso das pastilhas do gol 2010"
    )

    assert result.part_query == "pastilha de freio"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_canonicalizes_typo_plural_part_alias() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso de pstilhas do gol 2010"
    )

    assert result.part_query == "pastilha de freio"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_does_not_fuzzy_match_too_short_token() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero cox ecosport 2008"
    )
    assert result.part_query is None
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_uses_fuzzy_match_from_user_history() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "2008",
        last_messages=[
            {"role": "user", "text": "quero cuxim da ecosport"},
            {"role": "assistant", "text": "Qual o ano do veiculo?"},
        ],
    )
    assert result.part_query == "coxim"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


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


def test_llm_validator_keeps_fuzzy_dictionary_seed_when_llm_misses_part_query() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"vehicle_model":"EcoSport","vehicle_year":2008},'
                    '"missing_fields":[],"next_question":null,'
                    '"confidence":0.8}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("quero cuxim da ecosport 2008")

    assert result.decision == "search"
    assert result.criteria.part_query == "coxim"
    assert str(result.criteria.vehicle_model).lower() == "ecosport"
    assert result.criteria.vehicle_year == 2008
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


def test_llm_validator_merges_conversation_state_when_pending_slot_exists() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"engine":"1.6"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "1.6",
        conversation_state=ConversationState(
            criteria=SearchCriteria(part_query="batentes", vehicle_model="EcoSport"),
            pending_slot="engine",
            pending_question="Qual a motorizacao do veiculo?",
            last_decision="ask",
        ),
    )

    assert result.decision == "search"
    assert result.criteria.part_query == "batentes"
    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.engine == "1.6"


def test_llm_validator_preserves_llm_vehicle_year_question_when_part_code_is_irrelevant() -> None:
    validator = _validator(
        catalog=PreSearchCatalog(
            part_patterns=[
                ("amortecedor", ("amortecedor",)),
            ],
            brand_aliases={"Ford": ("ford",)},
            model_aliases={"EcoSport": ("ecosport",)},
            invalid_slot_tokens={"nao"},
            generic_ambiguous_parts=set(),
            needs_side=set(),
            needs_position=set(),
            needs_axle=set(),
            needs_engine=set(),
            needs_variant=set(),
            engine_by_model={"ecosport": ["1.6", "2.0", "Nao sei"]},
        )
    )
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"amortecedor","vehicle_model":"ECOSPORT"},'
                    '"missing_fields":["part_code"],'
                    '"next_question":{"type":"vehicle_year","key":"vehicle_year","prompt":"Qual ano do seu Ford EcoSport?"},'
                    '"confidence":0.35}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("quero amortecedor da ecosport")

    assert result.decision == "ask"
    assert result.missing_fields == ["vehicle_year"]
    assert result.next_question is not None
    assert result.next_question.key == "vehicle_year"
    assert result.next_question.prompt == "Qual ano do seu Ford EcoSport?"


def test_llm_validator_replaces_part_code_question_with_vehicle_year_when_part_query_exists() -> None:
    validator = _validator(
        catalog=PreSearchCatalog(
            part_patterns=[
                ("amortecedor", ("amortecedor",)),
            ],
            brand_aliases={"Ford": ("ford",)},
            model_aliases={"EcoSport": ("ecosport",)},
            invalid_slot_tokens={"nao"},
            generic_ambiguous_parts=set(),
            needs_side=set(),
            needs_position=set(),
            needs_axle=set(),
            needs_engine=set(),
            needs_variant=set(),
            engine_by_model={"ecosport": ["1.6", "2.0", "Nao sei"]},
        )
    )
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"amortecedor","vehicle_model":"ECOSPORT"},'
                    '"missing_fields":["part_code"],'
                    '"next_question":{"type":"request_info","key":"part_code","prompt":"Qual o codigo da peca?"},'
                    '"confidence":0.35}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("quero amortecedor da ecosport")

    assert result.decision == "ask"
    assert result.missing_fields == ["vehicle_year"]
    assert result.next_question is not None
    assert result.next_question.key == "vehicle_year"
    assert result.next_question.prompt == "Qual o ano do veiculo?"


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


def test_llm_validator_requires_side_for_bandejas_even_when_catalog_axle_rule_is_stale() -> None:
    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns,
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases=_catalog_fixture().model_aliases,
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side=set(),
        needs_position=set(),
        needs_axle={"bandejas"},
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
    )
    validator = _validator(catalog=catalog)
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

    assert result.decision == "ask"
    assert result.criteria.position == "front"
    assert result.next_question is not None
    assert result.next_question.key == "side"
    assert result.missing_fields == ["side"]


def test_llm_validator_specific_filter_ignores_stale_direction_rules() -> None:
    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns + [
            ("filtro de combustivel", ("filtro de combustivel", "filtro combustivel")),
        ],
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases={"EcoSport": ("ecosport",), "Gol": ("gol",), "2008": ("2008",)},
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side={"filtro de combustivel"},
        needs_position={"filtro de combustivel"},
        needs_axle={"filtro de combustivel"},
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"filtro de combustivel","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("filtro de combustivel gol 2010")

    assert result.decision == "search"
    assert result.missing_fields == []
    assert result.next_question is None


def test_llm_validator_position_satisfies_axle_requirement() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"coxim","vehicle_model":"Ecosport",'
                    '"vehicle_year":2008,"position":"dianteira"},"missing_fields":[],'
                    '"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns,
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases=_catalog_fixture().model_aliases,
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side=_catalog_fixture().needs_side,
        needs_position=_catalog_fixture().needs_position,
        needs_axle={"coxim"},
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"coxim","vehicle_model":"Ecosport",'
                    '"vehicle_year":2008,"position":"dianteira"},"missing_fields":[],'
                    '"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("coxim ecosport 2008 dianteira")

    assert result.decision == "search"
    assert result.missing_fields == []
    assert result.criteria.position == "front"
    assert result.criteria.axle is None


def test_llm_validator_uses_part_specific_score_threshold_when_configured() -> None:
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
        min_score_to_search=70,
        min_score_to_search_by_part={"coxim": 120},
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"coxim","vehicle_model":"Ecosport","vehicle_year":2008},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("coxim ecosport 2008")

    assert result.decision == "ask"
    assert result.next_question is not None
    assert result.next_question.key == "engine"
    assert "engine" in result.missing_fields


def test_llm_validator_promotes_answered_follow_up_to_search_when_requirements_are_met() -> None:
    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns,
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases=_catalog_fixture().model_aliases,
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side=_catalog_fixture().needs_side,
        needs_position=_catalog_fixture().needs_position,
        needs_axle={"coxim"},
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"position":"dianteiro"},"missing_fields":["axle"],'
                    '"next_question":{"type":"request_info","key":"axle","prompt":"Qual eixo do veiculo esta apresentando o problema?"},'
                    '"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "dianteiro",
        last_messages=[
            {"role": "user", "text": "coxim ecosport 2008"},
            {"role": "assistant", "text": "Qual eixo do veiculo esta apresentando o problema?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="coxim",
                vehicle_model="EcoSport",
                vehicle_year=2008,
            ),
            pending_slot="axle",
            pending_question="Qual eixo do veiculo esta apresentando o problema?",
            last_decision="ask",
        ),
    )

    assert result.decision == "search"
    assert result.missing_fields == []
    assert result.next_question is None
    assert result.criteria.part_query == "coxim"
    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.vehicle_year == 2008
    assert result.criteria.position == "front"


def test_llm_validator_does_not_promote_ask_without_follow_up_state() -> None:
    catalog = PreSearchCatalog(
        part_patterns=_catalog_fixture().part_patterns,
        brand_aliases=_catalog_fixture().brand_aliases,
        model_aliases=_catalog_fixture().model_aliases,
        invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
        generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
        needs_side=_catalog_fixture().needs_side,
        needs_position=_catalog_fixture().needs_position,
        needs_axle={"coxim"},
        needs_engine=_catalog_fixture().needs_engine,
        needs_variant=_catalog_fixture().needs_variant,
        engine_by_model=_catalog_fixture().engine_by_model,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"coxim","vehicle_model":"Ecosport",'
                    '"vehicle_year":2008,"position":"dianteiro"},"missing_fields":[],"next_question":null,'
                    '"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("coxim ecosport 2008 dianteiro")

    assert result.decision == "ask"
    assert result.next_question is not None
    assert result.next_question.key == "engine"
    assert result.missing_fields == ["engine"]


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


def test_llm_validator_asks_for_vehicle_year_when_only_part_query_and_model_are_present() -> None:
    validator = _validator()
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
    assert result.missing_fields == ["vehicle_year"]


def test_llm_validator_canonicalizes_llm_part_query_before_applying_rules() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"pastilha","vehicle_model":"Gol","vehicle_year":2010,"position":"dianteira"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("pastilha gol 2010 dianteira")

    assert result.decision == "search"
    assert result.criteria.part_query == "pastilha de freio"
    assert result.criteria.position == "front"


def test_llm_validator_rejects_non_catalog_part_query_and_asks_again() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"parafuso magico","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("parafuso magico gol 2010")

    assert result.decision == "ask"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "part_query"
    assert result.missing_fields == ["part_query"]


def test_llm_validator_chat_payload_includes_keep_alive() -> None:
    validator = _validator()

    payload = validator._build_chat_payload(
        message_text="coxim ecosport 2008",
        last_messages=[],
        dictionary_seed_criteria=SearchCriteria(part_query="coxim", vehicle_model="EcoSport", vehicle_year=2008),
        conversation_state=None,
    )

    assert payload["keep_alive"] == "1h"


def test_llm_validator_generate_payload_includes_keep_alive() -> None:
    validator = _validator()

    payload = validator._build_generate_payload(
        message_text="coxim ecosport 2008",
        last_messages=[],
        dictionary_seed_criteria=SearchCriteria(part_query="coxim", vehicle_model="EcoSport", vehicle_year=2008),
        conversation_state=None,
    )

    assert payload["keep_alive"] == "1h"


def test_llm_validator_warmup_payload_uses_keep_alive_and_minimal_generation() -> None:
    validator = _validator()

    payload = validator._build_warmup_payload()

    assert payload["model"] == "qwen2.5:7b"
    assert payload["keep_alive"] == "1h"
    assert payload["stream"] is False
    assert payload["options"]["num_predict"] == 1
    assert payload["options"]["temperature"] == 0.0
