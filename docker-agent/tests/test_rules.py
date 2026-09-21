import logging
import json
from dataclasses import replace
import csv
from pathlib import Path

import pytest

from app.core.domain.models import ConversationState
from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.domain.pre_search import SearchCriteria
from app.infra.erp_search_tools_pg import resolve_search_tools
from app.infra.pre_search_catalog_pg import PostgresPreSearchCatalogProvider
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
            ("amortecedores suspensao", ("amortecedores suspensao", "amortecedor suspensao", "suspensao", "suspencao")),
            ("pastilhas de freio", ("pastilha de freio", "pastilha freio", "pastilha", "pastilhas", "pastilhas de freio", "pstilhas")),
            ("discos de freio", ("disco de freio", "disco freio", "discos de freio")),
            ("lubrificantes", ("lubrificantes", "lubrificante", "oleo", "oleos")),
        ],
        brand_aliases={"Ford": ("ford",), "Chevrolet": ("chevrolet",)},
        model_aliases={
            "EcoSport": ("ecosport",),
            "Gol": ("gol",),
            "Corsa": ("corsa",),
            "2008": ("2008",),
        },
        invalid_slot_tokens={"nao"},
        generic_ambiguous_parts={"filtro"},
        needs_side={"bandejas"},
        needs_position={"amortecedores suspensao", "pastilhas de freio", "discos de freio", "coxim"},
        needs_axle=set(),
        needs_engine={"radiador"},
        needs_variant={"lubrificantes"},
        engine_by_model={
            "ecosport": ["1.6", "2.0", "ZETEC ROCAM", "DURATEC", "DURATEC HE", "SIGMA", "Nao sei"],
        },
        engine_options_by_model={
            "ecosport": [
                ("ZETEC ROCAM", 2003, 2012),
                ("DURATEC", 2004, 2017),
                ("DURATEC HE", 2003, 2012),
                ("SIGMA", 2012, None),
            ],
        },
        known_group_terms={"freio", "freios", "motor", "suspensao"},
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
        LLM_KEEP_ALIVE="1h",
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
        ERP_FALLBACK_DB_ENABLED=False,
    )

    with pytest.raises(RuntimeError):
        resolve_search_tools(settings=settings, logger=logging.getLogger("test"))


def test_catalog_provider_expands_group_terms() -> None:
    assert "freio" in PostgresPreSearchCatalogProvider._expand_group_terms("freios")
    assert "suspensao" in PostgresPreSearchCatalogProvider._expand_group_terms("suspensao")
    assert "motor" in PostgresPreSearchCatalogProvider._expand_group_terms("arrefecimento motor")


def test_model_brand_seed_links_known_models_to_existing_brands() -> None:
    mapping_path = Path("db/init/csv/vehicle_model_brand.csv")
    with mapping_path.open(encoding="utf-8", newline="") as source:
        mapping = {
            row["veiculo"]: row["montadora"]
            for row in csv.DictReader(source)
        }

    assert mapping["GOL"] == "VOLKSWAGEN"
    assert mapping["ECOSPORT"] == "FORD"
    assert mapping["CORSA"] == "CHEVROLET"
    assert mapping["CIVIC"] == "HONDA"

    bootstrap = Path("db/init/pre_search_init.sql").read_text(encoding="utf-8")
    assert "UPDATE pre_search_model" in bootstrap
    assert "vehicle_model_brand.csv" in bootstrap


def test_dictionary_extractor_extracts_part_model_and_year() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "Quero 2 unidade do filtro de oleo da ford ecosport 2008"
    )
    assert result.part_query == "filtro de oleo"
    assert result.vehicle_brand == "Ford"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008


def test_dictionary_extractor_extracts_oil_viscosity_as_variant() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "Quero oleo 20w50"
    )

    assert result.part_query == "lubrificantes"
    assert result.variant == "20W50"


@pytest.mark.parametrize(
    ("message", "expected_brand"),
    [
        ("jogo de velas NGK", "NGK"),
        ("amortecedor Cofap", "Cofap"),
        ("bandeja Nakata", "Nakata"),
        ("radiador Gol 2010 de preferencia Valeo", "Valeo"),
    ],
)
def test_dictionary_extractor_separates_product_brand_from_vehicle_brand(
    message: str,
    expected_brand: str,
) -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(message)

    assert result.preferred_product_brand == expected_brand
    assert result.vehicle_brand is None


def test_bare_coxim_asks_type_before_position_and_preserves_vehicle() -> None:
    catalog = replace(
        _catalog_fixture(),
        part_patterns=[
            ("coxins", ("coxim", "coxins", "coxim motor", "coxim cambio")),
            ("coxim amortecedor", ("coxim amortecedor", "coxim do amortecedor")),
        ],
        needs_position={"coxins"},
        needs_engine={"coxim amortecedor"},
    )
    validator = _validator(catalog=catalog)

    first = validator.try_validate_deterministic_ask(
        "quero coxim para ecosport 2008"
    )

    assert first is not None
    assert first.next_question is not None
    assert first.next_question.key == "coxim_type"
    assert first.next_question.options == [
        "Motor/câmbio", "Coxim do amortecedor", "Não sei"
    ]
    assert first.criteria.vehicle_model == "EcoSport"
    assert first.criteria.vehicle_year == 2008


def test_coxim_type_follow_up_routes_motor_and_amortecedor_individually() -> None:
    catalog = replace(
        _catalog_fixture(),
        part_patterns=[
            ("coxins", ("coxim", "coxins", "coxim motor", "coxim cambio")),
            ("coxim amortecedor", ("coxim amortecedor", "coxim do amortecedor")),
        ],
        needs_position={"coxins"},
        needs_engine={"coxim amortecedor"},
    )
    validator = _validator(catalog=catalog)
    criteria = SearchCriteria(
        part_query="coxins", vehicle_model="EcoSport", vehicle_year=2008
    )
    state = ConversationState(
        criteria=criteria,
        last_decision="ask",
        pending_slot="coxim_type",
        pending_question="O coxim é do motor/câmbio ou do amortecedor?",
    )

    motor = validator.try_validate_deterministic_ask(
        "motor/cambio", conversation_state=state
    )
    amortecedor = validator.try_validate_deterministic_ask(
        "coxim do amortecedor", conversation_state=state
    )

    assert motor is not None
    assert motor.criteria.part_query == "coxins"
    assert motor.next_question is not None
    assert motor.next_question.key == "position"
    assert amortecedor is not None
    assert amortecedor.criteria.part_query == "coxim amortecedor"
    assert amortecedor.next_question is not None
    assert amortecedor.next_question.key == "engine"


@pytest.mark.parametrize(
    ("message", "expected_brand"),
    [
        ("jogo de velas NGK", "NGK"),
        ("amortecedor Cofap", "Cofap"),
        ("bandeja Nakata", "Nakata"),
    ],
)
def test_dictionary_extractor_separates_product_brand_from_vehicle_brand(
    message: str,
    expected_brand: str,
) -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(message)

    assert result.preferred_product_brand == expected_brand
    assert result.vehicle_brand is None


def test_dictionary_extractor_does_not_turn_automotive_numbers_into_quantity() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    assert extractor.extract("radiador gol 2010 1.6").quantity is None
    assert extractor.extract("filtro Peugeot 206 2010 1600 cc 16v").quantity is None
    assert extractor.extract("filtro BMW 320i 2.0").quantity is None
    assert extractor.extract("2 unidades de filtro de oleo gol 2010").quantity == 2


def test_dictionary_extractor_preserves_composite_part_phrases() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    assert extractor.extract("polia da bomba d'agua do Focus").part_query == "polia bomba de agua"
    assert extractor.extract("kit corrente da bomba de oleo").part_query == "kit corrente bomba de oleo"
    assert extractor.extract("junta do cabecote").part_query == "junta do cabecote"


@pytest.mark.parametrize("message,expected", [
    ("tampa do radiador Gol 2010 1.0", "tampa radiador"),
    ("mangueira do radiador Gol 2010 1.0", "mangueiras de agua radiador"),
    ("kit do radiador Gol 2010 1.0", "kit radiador"),
    ("suporte do radiador Gol 2010 1.0", "suporte radiador"),
    ("reparo do radiador Gol 2010 1.0", "reparo radiador"),
])
def test_components_keep_their_own_identity(message, expected) -> None:
    from dataclasses import replace
    catalog = replace(_catalog_fixture(), part_patterns=_catalog_fixture().part_patterns + [
        ("tampa radiador", ("tampa radiador", "tampa do radiador")),
        ("mangueiras de agua radiador", ("mangueira radiador", "mangueira do radiador")),
    ])
    extractor = DictionaryPreSearchExtractor(catalog=catalog)
    result = extractor.extract(message)
    assert result.part_query == expected
    assert extractor.canonicalize_part_query(result.part_query) == expected
    assert extractor.extract_items(message)[0].part_query == expected


def test_dictionary_extractor_builds_independent_items_with_shared_vehicle() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "2 unidades de filtro de oleo e pastilha de freio da ecosport 2008"
    )

    assert [item.part_query for item in items] == ["filtro de oleo", "pastilhas de freio"]
    assert all(item.vehicle_model == "EcoSport" for item in items)
    assert all(item.vehicle_year == 2008 for item in items)
    assert items[0].quantity == 2


def _real_multi_item_catalog() -> PreSearchCatalog:
    """Representative catalog aliases; boundaries still come from the catalog."""
    base = _catalog_fixture()
    return replace(
        base,
        part_patterns=base.part_patterns + [
            ("barras", ("barra axial",)),
            ("bandejas", ("balanca completa",)),
            ("amortecedores suspensao", ("amortecedor", "amortecedor dianteiro", "amortecedor traseiro")),
            ("coxim", ("coxim dianteiro com rolamento", "coxim traseiro")),
            ("batentes", ("kit batente coifa", "kit coifa e batente")),
            ("tambores de freio", ("tambor traseiro", "tambor")),
            ("lonas", ("lona traseira", "lona")),
            ("rolamentos", ("rolamento",)),
            ("calco caixa", ("calco caixa",)),
            ("juntas", ("jogo juntas tampa de valvulas e carter",)),
            ("correia alternador", ("correia do alternador",)),
            ("buchas", ("bucha do eixo traseiro",)),
            ("discos de freio", ("disco dianteiro",)),
        ],
        brand_aliases={**base.brand_aliases, "Fiat": ("fiat",), "Renault": ("renault",)},
        model_aliases={
            **base.model_aliases,
            "Gran Siena": ("gran siena",),
            "Siena": ("siena",),
            "Kwid": ("kwid",),
        },
    )


def test_real_005_keeps_catalog_items_quantities_and_shared_leading_vehicle() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_real_multi_item_catalog())

    items = extractor.extract_items(
        "Fiat Gran Siena actrative 2017/18 1.4 2 barra Axial LD /LE "
        "2 balança completa LE/LD 2 coxim dianteiro com rolamento Kit batente coifa dianteiro "
        "2 coxim traseiro LE/LD 2 disco freio dianteiro 1 kit pastilha dianteiro "
        "2 tambor traseiro Par de lona traseira"
    )

    assert [item.part_query for item in items] == [
        "barras", "bandejas", "coxim", "batentes", "coxim",
        "discos de freio", "pastilhas de freio", "tambores de freio", "lonas",
    ]
    assert [item.quantity for item in items] == [2, 2, 2, None, 2, 2, 1, 2, 2]
    assert all(item.vehicle_model == "Gran Siena" for item in items)
    assert all(item.vehicle_year == 2017 for item in items)
    assert all(item.engine == "1.4" for item in items)


def test_real_052_and_real_055_keep_each_vehicle_local_to_its_item() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_real_multi_item_catalog())

    gol_items = extractor.extract_items(
        "Preciso do jogo de amortecedor dianteiro do gol g5 2012 E "
        "jogo de disco de freio dianteiro do gol g5 2012"
    )
    mixed_items = extractor.extract_items(
        "Valor rolamento gol 98 Amortecedor Siena 2008 dianteiro E Pastilha frio Siena 2008"
    )

    assert [item.part_query for item in gol_items] == ["amortecedores suspensao", "discos de freio"]
    assert all(item.vehicle_model == "Gol" and item.vehicle_year == 2012 for item in gol_items)
    assert [item.part_query for item in mixed_items] == ["rolamentos", "amortecedores suspensao", "pastilhas de freio"]
    assert [item.vehicle_model for item in mixed_items] == ["Gol", "Siena", "Siena"]
    assert [item.vehicle_year for item in mixed_items] == [1998, 2008, 2008]


def test_real_067_and_real_081_preserve_partial_items_without_vehicle_contamination() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_real_multi_item_catalog())

    kwid_items = extractor.extract_items(
        "Calço caixa Pastilhas de freio dianteira Disco dianteiro Jogo juntas tampa de válvulas e carter "
        "Correia do alternador 4 litros de oleo 5w30 Filtro de óleo do motor Kwid 2020"
    )
    corsa_items = extractor.extract_items(
        "Bom dia,2,amortecedor traseiro corsa sedam premium 2007/2008,2 bucha do eixo traseiro,2 kit coifa e batente traseiro"
    )

    assert [item.part_query for item in kwid_items] == [
        "calco caixa", "pastilhas de freio", "discos de freio", "juntas",
        "correia alternador", "lubrificantes", "filtro de oleo",
    ]
    assert all(item.vehicle_model == "Kwid" and item.vehicle_year == 2020 for item in kwid_items)
    assert [item.part_query for item in corsa_items] == ["amortecedores suspensao", "buchas", "batentes"]
    assert corsa_items[0].vehicle_model == "Corsa"
    assert corsa_items[0].vehicle_year == 2007
    assert all(item.vehicle_model is None for item in corsa_items[1:])


def test_dictionary_extractor_resolves_directional_negation_to_the_affirmative_position() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    result = extractor.extract("pastilha traseira do Gol 2010, nao dianteira")

    assert result.part_query == "pastilhas de freio"
    assert result.position == "rear"


def test_dictionary_extractor_keeps_only_the_replacement_part_in_items() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "nao quero radiador, quero filtro de oleo Gol 2010 1.0"
    )

    assert [item.part_query for item in items] == ["filtro de oleo"]
    assert items[0].vehicle_model == "Gol"
    assert items[0].engine == "1.0"


def test_dictionary_extractor_uses_an_explicit_correction_value() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    result = extractor.extract("corrigindo, lado esquerdo")

    assert result.side == "left"


def test_dictionary_extractor_does_not_emit_a_negative_part_as_an_item() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    assert extractor.extract_items("nao quero radiador") == []


def test_dictionary_extractor_keeps_same_family_for_distinct_vehicles() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "radiador Gol 2010 1.0 e radiador Corsa 2011 1.4"
    )

    assert len(items) == 2
    assert [item.part_query for item in items] == ["radiador", "radiador"]
    assert [item.vehicle_model for item in items] == ["Gol", "Corsa"]
    assert [item.vehicle_year for item in items] == [2010, 2011]
    assert [item.engine for item in items] == ["1.0", "1.4"]


def test_dictionary_extractor_does_not_copy_vehicle_between_distinct_clauses() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "radiador Gol 2010 1.0 e pastilha de freio traseira"
    )

    assert len(items) == 2
    assert items[0].vehicle_model == "Gol"
    assert items[0].vehicle_year == 2010
    assert items[0].engine == "1.0"
    assert items[1].part_query == "pastilhas de freio"
    assert items[1].vehicle_model is None
    assert items[1].vehicle_year is None
    assert items[1].engine is None


def test_dictionary_extractor_shares_only_a_trailing_explicit_vehicle_application() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "radiador e pastilha de freio traseira para Gol 2010 1.0"
    )

    assert len(items) == 2
    assert all(item.vehicle_model == "Gol" for item in items)
    assert all(item.vehicle_year == 2010 for item in items)
    assert all(item.engine == "1.0" for item in items)


def test_dictionary_extractor_builds_independent_items_with_shared_vehicle() -> None:
    extractor = DictionaryPreSearchExtractor(catalog=_catalog_fixture())

    items = extractor.extract_items(
        "2 unidades de filtro de oleo e pastilha de freio da ecosport 2008"
    )

    assert [item.part_query for item in items] == ["filtro de oleo", "pastilhas de freio"]
    assert all(item.vehicle_model == "EcoSport" for item in items)
    assert all(item.vehicle_year == 2008 for item in items)
    assert items[0].quantity == 2


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
    assert result.position is None


def test_dictionary_extractor_keeps_position_separate_from_axle() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero coxim dianteiro da ecosport"
    )

    assert result.position == "front"
    assert result.axle is None


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        ("dianteiro", "front"),
        ("dianteira", "front"),
        ("traseiro", "rear"),
        ("traseira", "rear"),
    ],
)
def test_dictionary_extractor_normalizes_direction_grammatical_gender(
    direction: str,
    expected: str,
) -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        f"pastilha de freio gol 2010 {direction}"
    )

    assert result.position == expected


def test_pastilhas_with_vehicle_and_position_do_not_require_engine() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"pastilhas de freio",'
                    '"vehicle_model":"Corsa","vehicle_year":2011,"position":"dianteira"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("pastilha freio corsa 2011 dianteira")

    assert result.decision == "search"
    assert result.criteria.part_query == "pastilhas de freio"
    assert result.criteria.position == "front"
    assert "engine" not in result.missing_fields


def test_dictionary_extractor_keeps_spontaneous_variant_information() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "com ABS"
    )

    assert result.variant == "ABS"


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


def test_dictionary_extractor_rejects_part_name_followed_by_year_as_part_code() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "pastilha de freio 2010 1.0"
    )

    assert result.part_query == "pastilhas de freio"
    assert result.part_code is None
    assert result.vehicle_year == 2010
    assert result.engine == "1.0"


def test_dictionary_extractor_accepts_space_separated_code_with_explicit_marker() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero consultar o codigo AB 1234"
    )

    assert result.part_code == "AB-1234"


def test_dictionary_extractor_accepts_space_separated_code_with_abbreviated_marker() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "quero consultar o cod. AB 1234"
    )

    assert result.part_code == "AB-1234"


def test_dictionary_extractor_accepts_explicit_part_code_from_user_history() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "pode consultar",
        last_messages=[
            {"role": "user", "text": "o codigo e AB-1234"},
            {"role": "assistant", "text": "Vou verificar."},
        ],
    )

    assert result.part_code == "AB-1234"


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

    assert result.part_query == "pastilhas de freio"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_canonicalizes_typo_plural_part_alias() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso de pstilhas do gol 2010"
    )

    assert result.part_query == "pastilhas de freio"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_canonicalizes_singular_brake_disc_alias() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso de disco de freio do gol 2010"
    )

    assert result.part_query == "discos de freio"
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_does_not_accept_non_catalog_part_family() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "preciso de farol do gol 2010"
    )

    assert result.part_query is None
    assert result.vehicle_model == "Gol"
    assert result.vehicle_year == 2010


def test_dictionary_extractor_canonicalizes_suspension_typo_alias() -> None:
    result = DictionaryPreSearchExtractor(catalog=_catalog_fixture()).extract(
        "voces tem a suspencao da ecosport 2008 1.6?"
    )

    assert result.part_query == "amortecedores suspensao"
    assert result.vehicle_model == "EcoSport"
    assert result.vehicle_year == 2008
    assert result.engine == "1.6"


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


def test_multi_item_gate_keeps_each_vehicle_and_requirement_independent() -> None:
    validator = _validator()

    radiator = validator.validate_item_for_search(
        SearchCriteria(
            part_query="radiador",
            vehicle_model="Gol",
            vehicle_year=2010,
            engine="1.0",
        ),
        message_text="radiador Gol 2010 1.0 e bandeja Corsa 2011",
    )
    tray = validator.validate_item_for_search(
        SearchCriteria(
            part_query="bandeja",
            vehicle_model="Corsa",
            vehicle_year=2011,
        ),
        message_text="radiador Gol 2010 1.0 e bandeja Corsa 2011",
    )

    assert radiator.decision == "search"
    assert radiator.criteria.vehicle_model == "Gol"
    assert radiator.criteria.engine == "1.0"
    assert tray.decision == "ask"
    assert tray.criteria.vehicle_model == "Corsa"
    assert tray.criteria.engine is None
    assert "side" in tray.missing_fields


def test_multi_item_gate_rejects_part_code_not_present_in_user_evidence() -> None:
    validator = _validator()

    result = validator.validate_item_for_search(
        SearchCriteria(part_code="ZZ-12345"),
        message_text="preciso de uma peca para o Gol 2010",
    )

    assert result.decision == "ask"
    assert result.criteria.part_code is None
    assert result.missing_fields == ["part_query"]


def test_llm_validator_does_not_ask_for_optional_side_when_search_gate_is_complete() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"radiador",'
                    '"vehicle_model":"Corsa","vehicle_year":2011,"engine":"1.4"},'
                    '"missing_fields":["side"],'
                    '"next_question":{"type":"request_info","key":"side","prompt":"Qual lado?"},'
                    '"confidence":0.8}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("radiador Corsa 2011 1.4")

    assert result.decision == "search"
    assert result.criteria.vehicle_model == "Corsa"
    assert result.missing_fields == []
    assert result.next_question is None


def test_llm_validator_uses_deterministic_item_boundaries_before_llm_output() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"radiador",'
                    '"vehicle_model":"Corsa","vehicle_year":2010,"engine":"1.0"},'
                    '"missing_fields":["vehicle_brand"],'
                    '"next_question":{"type":"request_info","key":"vehicle_brand","prompt":"Qual marca?"},'
                    '"confidence":0.8}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("radiador Gol 2010 1.0 e bandeja Corsa 2011")

    assert result.decision == "search"
    assert result.criteria == SearchCriteria(
        part_query="radiador",
        vehicle_model="Gol",
        vehicle_year=2010,
        engine="1.0",
    )
    assert result.items == [
        SearchCriteria(
            part_query="radiador",
            vehicle_model="Gol",
            vehicle_year=2010,
            engine="1.0",
        ),
        SearchCriteria(
            part_query="bandejas",
            vehicle_model="Corsa",
            vehicle_year=2011,
        ),
    ]


def test_llm_validator_keeps_active_multi_item_when_applying_short_follow_up() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"radiador",'
                    '"vehicle_model":"Gol","vehicle_year":2010,"engine":"1.0","side":"left"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "esquerda",
        last_messages=[{"role": "user", "text": "radiador Gol 2010 1.0 e bandeja Corsa 2011"}],
        conversation_state=ConversationState(
            criteria=SearchCriteria(part_query="bandejas", vehicle_model="Corsa", vehicle_year=2011),
            items=[
                SearchCriteria(part_query="radiador", vehicle_model="Gol", vehicle_year=2010, engine="1.0"),
                SearchCriteria(part_query="bandejas", vehicle_model="Corsa", vehicle_year=2011),
            ],
            active_item_index=1,
            pending_slot="side",
            pending_question="Qual lado da bandeja?",
            last_decision="ask",
        ),
    )

    assert result.decision == "search"
    assert result.criteria == SearchCriteria(
        part_query="bandejas",
        vehicle_model="Corsa",
        vehicle_year=2011,
        side="left",
    )


def test_llm_validator_blocks_freio_2010_from_real_follow_up_case() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"pastilhas de freio",'
                    '"part_code":"FREIO-2010","vehicle_model":"Gol","vehicle_year":2010,'
                    '"engine":"1.0","quantity":1},"missing_fields":[],"next_question":null,'
                    '"confidence":0.94}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "pastilha de freio 2010 1.0",
        last_messages=[
            {"role": "user", "text": "preciso de ajuda com uma peca do gol"},
            {"role": "assistant", "text": "Qual a familia da peca que voce precisa?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(vehicle_model="Gol"),
            pending_slot="part_query",
            pending_question="Qual a familia da peca que voce precisa?",
            last_decision="ask",
        ),
    )

    assert result.criteria.part_code is None
    assert result.criteria.part_query == "pastilhas de freio"
    assert result.decision == "ask"
    assert "position" in result.missing_fields


def test_llm_validator_does_not_restore_unproven_part_code_from_conversation_state() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"pastilhas de freio",'
                    '"vehicle_model":"Gol","vehicle_year":2010,"engine":"1.0"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "1.0",
        last_messages=[
            {"role": "user", "text": "pastilha de freio gol 2010"},
            {"role": "assistant", "text": "Qual a motorizacao?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="pastilhas de freio",
                part_code="FREIO-2010",
                vehicle_model="Gol",
                vehicle_year=2010,
            ),
            pending_slot="engine",
            pending_question="Qual a motorizacao?",
            last_decision="ask",
        ),
    )

    assert result.criteria.part_code is None
    assert result.decision == "ask"
    assert "position" in result.missing_fields


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


def test_llm_validator_keeps_fuzzy_dictionary_seed_and_applies_coxim_position_rule() -> None:
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

    assert result.decision == "ask"
    assert result.criteria.part_query == "coxim"
    assert str(result.criteria.vehicle_model).lower() == "ecosport"
    assert result.criteria.vehicle_year == 2008
    assert result.missing_fields == ["position"]
    assert result.next_question is not None
    assert result.next_question.key == "position"


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
    assert str(result.criteria.vehicle_model).lower() == "ecosport"
    assert result.criteria.engine == "1.6"


def test_current_message_identity_overrides_old_state_and_llm_identity() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":"radiador",'
                    '"vehicle_model":"Gol","vehicle_year":2010,"engine":null},'
                    '"missing_fields":["engine"],"next_question":{"key":"engine",'
                    '"prompt":"Qual a motorizacao?"},"confidence":0.8}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(
        "radiador ecosport 2008 1.6",
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="radiador", vehicle_model="Gol", vehicle_year=2010
            ),
            pending_slot="engine",
            pending_question="Qual a motorizacao?",
            last_decision="ask",
        ),
    )

    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.vehicle_year == 2008
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


def test_llm_validator_uses_catalog_rule_for_specific_filter() -> None:
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

    assert result.decision == "ask"
    assert result.missing_fields == ["side", "position", "axle"]
    assert result.next_question is not None
    assert result.next_question.key == "side"


@pytest.mark.parametrize(
    ("part_query", "aliases", "message"),
    [
        ("filtro de oleo", ("filtro de oleo", "filtro oleo"), "filtro de oleo gol 2010"),
        (
            "filtro de ar do motor",
            ("filtro de ar do motor", "filtro ar motor"),
            "filtro de ar do motor gol 2010",
        ),
        (
            "filtro de combustivel",
            ("filtro de combustivel", "filtro combustivel"),
            "filtro de combustivel gol 2010",
        ),
    ],
)
def test_llm_validator_does_not_request_directional_slots_for_corrected_filter_catalog(
    part_query: str,
    aliases: tuple[str, ...],
    message: str,
) -> None:
    base_catalog = _catalog_fixture()
    part_patterns = [
        pattern
        for pattern in base_catalog.part_patterns
        if pattern[0] != part_query
    ]
    part_patterns.append((part_query, aliases))
    catalog = PreSearchCatalog(
        part_patterns=part_patterns,
        brand_aliases=base_catalog.brand_aliases,
        model_aliases=base_catalog.model_aliases,
        invalid_slot_tokens=base_catalog.invalid_slot_tokens,
        generic_ambiguous_parts=base_catalog.generic_ambiguous_parts,
        needs_side=base_catalog.needs_side,
        needs_position=base_catalog.needs_position,
        needs_axle=base_catalog.needs_axle,
        needs_engine=base_catalog.needs_engine,
        needs_variant=base_catalog.needs_variant,
        engine_by_model=base_catalog.engine_by_model,
    )
    validator = _validator(catalog=catalog)
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    f'{{"decision":"search","criteria":{{"part_query":"{part_query}",'
                    '"vehicle_model":"Gol","vehicle_year":2010},"missing_fields":[],'
                    '"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate(message)

    assert result.decision == "search"
    assert result.missing_fields == []
    assert result.next_question is None


def test_deterministic_validator_bypasses_complete_exact_request() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically(
        "radiador gol 2010 1.0"
    )

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.part_query == "radiador"
    assert result.criteria.vehicle_model == "Gol"
    assert result.criteria.vehicle_year == 2010
    assert result.criteria.engine == "1.0"
    assert result.missing_fields == []
    audit = validator.get_last_audit()
    assert audit is not None
    assert audit["pre_search_path"] == "deterministic_bypass"
    assert audit["deterministic_reason"] == "complete_request"
    assert audit["llm_endpoint_used"] is None


def test_deterministic_validator_bypasses_literal_part_code() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically("codigo AB-1234")

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.part_code == "AB-1234"


def test_deterministic_validator_bypasses_simple_follow_up() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically(
        "1.0",
        last_messages=[
            {"role": "user", "text": "radiador gol 2010"},
            {"role": "assistant", "text": "Qual a motorizacao do veiculo?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="radiador",
                vehicle_model="Gol",
                vehicle_year=2010,
            ),
            pending_slot="engine",
            pending_question="Qual a motorizacao do veiculo?",
            last_decision="ask",
        ),
    )

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.engine == "1.0"
    audit = validator.get_last_audit()
    assert audit is not None
    assert audit["deterministic_reason"] == "complete_follow_up"


def test_deterministic_ask_follow_up_year_preserves_vehicle_model_and_asks_next_field() -> None:
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
    )
    validator = _validator(catalog=catalog)

    result = validator.try_validate_deterministic_ask(
        "2008",
        last_messages=[
            {"role": "user", "text": "quero coxim para ecosport"},
            {"role": "assistant", "text": "Qual o ano do veiculo?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(part_query="coxim", vehicle_model="EcoSport"),
            pending_slot="vehicle_year",
            pending_question="Qual o ano do veiculo?",
            last_decision="ask",
        ),
    )

    assert result is not None
    assert result.decision == "ask"
    assert result.criteria.part_query == "coxim"
    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.vehicle_year == 2008
    assert result.missing_fields == ["position"]
    assert result.next_question is not None
    assert result.next_question.key == "position"
    audit = validator.get_last_audit()
    assert audit is not None
    assert audit["deterministic_reason"] == "complete_follow_up_missing_field"


def test_deterministic_validator_uses_direction_answer_for_pending_coxim_position() -> None:
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
    )
    validator = _validator(catalog=catalog)

    result = validator.try_validate_deterministically(
        "dianteiro",
        last_messages=[
            {"role": "user", "text": "coxim ecosport 2008"},
            {"role": "assistant", "text": "Qual a posicao da peca?"},
        ],
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="coxim",
                vehicle_model="EcoSport",
                vehicle_year=2008,
            ),
            pending_slot="position",
            pending_question="Qual a posicao da peca?",
            last_decision="ask",
        ),
    )

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.vehicle_year == 2008
    assert result.criteria.position == "front"
    assert result.criteria.axle is None


def test_deterministic_follow_up_coxim_ecosport_year_then_position_searches() -> None:
    """Regression for the VPS flow: EcoSport -> 2008 -> dianteiro."""

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
    )
    validator = _validator(catalog=catalog)
    initial_state = ConversationState(
        criteria=SearchCriteria(part_query="coxim", vehicle_model="EcoSport"),
        pending_slot="vehicle_year",
        pending_question="Qual o ano do veiculo?",
        last_decision="ask",
    )

    year_result = validator.try_validate_deterministic_ask(
        "2008",
        last_messages=[
            {"role": "user", "text": "quero coxim para ecosport"},
            {"role": "assistant", "text": "Qual o ano do veiculo?"},
        ],
        conversation_state=initial_state,
    )

    assert year_result is not None
    assert year_result.next_question is not None
    assert year_result.next_question.key == "position"
    assert year_result.criteria.vehicle_model == "EcoSport"
    assert year_result.criteria.vehicle_year == 2008

    axle_result = validator.try_validate_deterministically(
        "dianteiro",
        last_messages=[
            {"role": "user", "text": "quero coxim para ecosport"},
            {"role": "assistant", "text": "Qual o ano do veiculo?"},
            {"role": "user", "text": "2008"},
            {"role": "assistant", "text": "Qual a posicao do coxim?"},
        ],
        conversation_state=ConversationState(
            criteria=year_result.criteria,
            pending_slot="position",
            pending_question="Qual a posicao do coxim?",
            last_decision="ask",
        ),
    )

    assert axle_result is not None
    assert axle_result.decision == "search"
    assert axle_result.criteria.vehicle_model == "EcoSport"
    assert axle_result.criteria.vehicle_year == 2008
    assert axle_result.criteria.position == "front"
    assert axle_result.criteria.axle is None


@pytest.mark.parametrize(
    ("message", "conversation_state"),
    [
        ("radiador gol 2010", None),
        ("rdiador gol 2010 1.0", None),
        ("filtro gol 2010", None),
    ],
)
def test_deterministic_validator_keeps_uncertain_cases_on_llm_path(
    message: str,
    conversation_state: ConversationState | None,
) -> None:
    validator = _validator()

    result = validator.try_validate_deterministically(
        message,
        conversation_state=conversation_state,
    )

    assert result is None
    assert validator.get_last_audit() is None


@pytest.mark.parametrize(
    ("answer", "model", "year", "expected_engine"),
    [
        ("zetec rocam", "EcoSport", 2008, "ZETEC ROCAM"),
        ("duratec", "EcoSport", 2008, "DURATEC"),
        ("duratec he", "EcoSport", 2008, "DURATEC HE"),
        ("sigma", "EcoSport", 2016, "SIGMA"),
        ("ea111", "Gol", 2010, "EA111"),
        ("ea211", "Gol", 2016, "EA211"),
        ("BE", "Corsa", 2000, "BE"),
    ],
)
def test_deterministic_engine_follow_up_accepts_catalog_text_option(
    answer: str,
    model: str,
    year: int,
    expected_engine: str,
) -> None:
    base = _catalog_fixture()
    engine_by_model = dict(base.engine_by_model)
    engine_options_by_model = dict(base.engine_options_by_model)
    if model.lower() == "corsa":
        engine_by_model["corsa"] = ["BE", "VHC", "Nao sei"]
        engine_options_by_model["corsa"] = [("BE", 1998, 2001), ("VHC", 2002, 2011)]
    if model.lower() == "gol":
        engine_by_model["gol"] = ["EA111", "EA211", "Nao sei"]
        engine_options_by_model["gol"] = [("EA111", 2008, 2018), ("EA211", 2014, None)]
    validator = _validator(catalog=replace(
        base,
        engine_by_model=engine_by_model,
        engine_options_by_model=engine_options_by_model,
    ))
    state = ConversationState(
        criteria=SearchCriteria(
            part_query="radiador",
            vehicle_model=model,
            vehicle_year=year,
        ),
        pending_slot="engine",
        pending_question="Qual a motorizacao do veiculo?",
        last_decision="ask",
    )

    result = validator.try_validate_deterministically(answer, conversation_state=state)

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.engine == expected_engine


def test_deterministic_engine_follow_up_keeps_year_incompatible_option_unresolved() -> None:
    validator = _validator()
    state = ConversationState(
        criteria=SearchCriteria(part_query="radiador", vehicle_model="EcoSport", vehicle_year=2008),
        pending_slot="engine",
        pending_question="Qual a motorizacao do veiculo?",
        last_decision="ask",
    )

    assert validator.try_validate_deterministically("sigma", conversation_state=state) is None


def test_coxim_amortecedor_engine_follow_up_preserves_textual_engine_for_next_question() -> None:
    catalog = replace(
        _catalog_fixture(),
        part_patterns=_catalog_fixture().part_patterns + [
            ("coxim amortecedor", ("coxim amortecedor",)),
        ],
        needs_position={*_catalog_fixture().needs_position, "coxim amortecedor"},
    )
    validator = _validator(catalog=catalog)
    state = ConversationState(
        criteria=SearchCriteria(
            part_query="coxim amortecedor",
            vehicle_model="EcoSport",
            vehicle_year=2008,
        ),
        pending_slot="engine",
        pending_question="Qual a motorizacao do veiculo?",
        last_decision="ask",
    )

    result = validator.try_validate_deterministic_ask("zetec rocam", conversation_state=state)

    assert result is not None
    assert result.criteria.engine == "ZETEC ROCAM"
    assert result.next_question is not None
    assert result.next_question.key == "position"


def test_deterministic_ask_policy_accepts_exact_family_with_governed_missing_field() -> None:
    validator = _validator()

    result = validator.evaluate_deterministic_ask_eligibility("radiador gol 2010")

    assert result.eligible is True
    assert result.reason == "exact_family_missing_field"
    assert result.criteria.part_query == "radiador"
    assert result.missing_fields == ("engine",)
    assert result.next_question is not None
    assert result.next_question.key == "engine"
    assert result.next_question.prompt == "Qual a motorizacao do veiculo?"


def test_deterministic_ask_requests_oil_specification_without_vehicle_data() -> None:
    validator = _validator()

    result = validator.try_validate_deterministic_ask("quero oleo")

    assert result is not None
    assert result.decision == "ask"
    assert result.criteria.part_query == "lubrificantes"
    assert result.missing_fields == ["variant"]
    assert result.next_question is not None
    assert result.next_question.key == "variant"
    assert result.next_question.prompt == "Qual a especificacao do oleo (por exemplo, 20W50)?"


def test_deterministic_bypass_searches_oil_when_specification_is_present() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically("quero oleo 20w50")

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.part_query == "lubrificantes"
    assert result.criteria.variant == "20W50"
    assert result.criteria.vehicle_model is None
    assert result.missing_fields == []


@pytest.mark.parametrize("message", ["quero uma peca", "preciso de um item automotivo"])
def test_deterministic_ask_policy_accepts_explicit_generic_automotive_request(
    message: str,
) -> None:
    validator = _validator()

    result = validator.evaluate_deterministic_ask_eligibility(message)

    assert result.eligible is True
    assert result.reason == "explicit_generic_part_request"
    assert result.criteria.part_query is None
    assert result.missing_fields == ("part_query",)
    assert result.next_question is not None
    assert result.next_question.key == "part_query"


def test_deterministic_ask_policy_uses_stable_priority_for_multiple_missing_fields() -> None:
    base_catalog = _catalog_fixture()
    catalog = PreSearchCatalog(
        part_patterns=base_catalog.part_patterns,
        brand_aliases=base_catalog.brand_aliases,
        model_aliases=base_catalog.model_aliases,
        invalid_slot_tokens=base_catalog.invalid_slot_tokens,
        generic_ambiguous_parts=base_catalog.generic_ambiguous_parts,
        needs_side={*base_catalog.needs_side, "radiador"},
        needs_position=base_catalog.needs_position,
        needs_axle=base_catalog.needs_axle,
        needs_engine=base_catalog.needs_engine,
        needs_variant=base_catalog.needs_variant,
        engine_by_model=base_catalog.engine_by_model,
    )
    validator = _validator(catalog=catalog)

    result = validator.evaluate_deterministic_ask_eligibility("radiador gol 2010")

    assert result.eligible is True
    assert result.missing_fields == ("engine", "side")
    assert result.next_question is not None
    assert result.next_question.key == "engine"


@pytest.mark.parametrize(
    ("message", "expected_reason"),
    [
        ("rdiador gol 2010", "part_query_not_exact"),
        ("quero aquilo que evita o carro de ficar pulando", "functional_description"),
        ("quero uma peca que segura o carro", "functional_description"),
        ("radiador que serve para resfriar o gol 2010", "functional_description"),
        ("estou com barulho no carro", "symptom_description"),
        ("radiador gol 2010 vazando", "symptom_description"),
        ("esquece o radiador, quero outra peca", "subject_change"),
        ("quero falar com um vendedor", "handoff_intent"),
        ("radiador gol 2010, quero falar com um vendedor", "handoff_intent"),
        ("quero uma peca chamada farol para gol 2010", "unresolved_part_description"),
        ("bom dia, tenho um gol 2010", "part_request_not_explicit"),
        ("radiador gol 2010 1.0", "no_missing_field"),
    ],
)
def test_deterministic_ask_policy_rejects_unsafe_or_unresolved_cases(
    message: str,
    expected_reason: str,
) -> None:
    validator = _validator()

    result = validator.evaluate_deterministic_ask_eligibility(message)

    assert result.eligible is False
    assert result.reason == expected_reason
    assert result.next_question is None


def test_deterministic_ask_policy_does_not_override_active_pending_slot() -> None:
    validator = _validator()

    result = validator.evaluate_deterministic_ask_eligibility(
        "radiador gol 2010",
        conversation_state=ConversationState(
            criteria=SearchCriteria(part_query="bandejas", vehicle_model="EcoSport"),
            pending_slot="side",
            pending_question="Qual lado da peca?",
            last_decision="ask",
        ),
    )

    assert result.eligible is False
    assert result.reason == "active_pending_slot"


def test_deterministic_bypass_preserves_rear_when_front_is_negated() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically(
        "pastilha traseira do Gol 2010, nao dianteira"
    )

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.part_query == "pastilhas de freio"
    assert result.criteria.position == "rear"


def test_deterministic_bypass_uses_only_the_explicit_replacement_part() -> None:
    validator = _validator()

    result = validator.try_validate_deterministically(
        "nao quero radiador, quero filtro de oleo Gol 2010 1.0"
    )

    assert result is not None
    assert result.decision == "search"
    assert result.criteria.part_query == "filtro de oleo"
    assert result.criteria.engine == "1.0"


def test_unresolved_negation_is_asked_before_deterministic_bypass_or_llm() -> None:
    validator = _validator()

    assert validator.try_validate_deterministically("nao quero radiador") is None
    result = validator.try_validate_deterministic_ask("nao quero radiador")

    assert result is not None
    assert result.decision == "ask"
    assert result.missing_fields == ["intent_resolution"]
    assert result.next_question is not None
    assert result.next_question.key == "intent_resolution"

    validator._post_chat_or_generate = lambda **kwargs: pytest.fail("LLM nao deve ser chamada")
    result = validator.validate("nao quero radiador")

    assert result.decision == "ask"
    assert result.next_question is not None
    assert result.next_question.key == "intent_resolution"


def test_conflicting_vehicle_brand_and_model_requires_confirmation() -> None:
    validator = _validator(
        catalog=PreSearchCatalog(
            part_patterns=_catalog_fixture().part_patterns,
            brand_aliases={"Honda": ("honda",)},
            model_aliases=_catalog_fixture().model_aliases,
            invalid_slot_tokens=_catalog_fixture().invalid_slot_tokens,
            generic_ambiguous_parts=_catalog_fixture().generic_ambiguous_parts,
            needs_side=_catalog_fixture().needs_side,
            needs_position=_catalog_fixture().needs_position,
            needs_axle=_catalog_fixture().needs_axle,
            needs_engine=_catalog_fixture().needs_engine,
            needs_variant=_catalog_fixture().needs_variant,
            engine_by_model=_catalog_fixture().engine_by_model,
        )
    )

    assert validator.try_validate_deterministically("pastilha Honda Gol 2010 traseira") is None
    result = validator.try_validate_deterministic_ask(
        "pastilha Honda Gol 2010 traseira"
    )

    assert result is not None
    assert result.decision == "ask"
    assert result.missing_fields == ["vehicle_identity"]
    assert result.next_question is not None
    assert result.next_question.key == "vehicle_identity"


def test_deterministic_ask_returns_governed_validation_with_canonical_family() -> None:
    validator = _validator()

    result = validator.try_validate_deterministic_ask("bandeja ecosport 2008")

    assert result is not None
    assert result.decision == "ask"
    assert result.criteria.part_query == "bandejas"
    assert result.criteria.vehicle_model == "EcoSport"
    assert result.criteria.vehicle_year == 2008
    assert result.criteria.part_code is None
    assert result.missing_fields == ["side"]
    assert result.next_question is not None
    assert result.next_question.key == "side"
    assert result.next_question.options == ["Esquerdo", "Direito", "Nao sei"]
    assert result.confidence == 0.99
    assert validator.get_last_audit() == {
        "llm_endpoint_used": None,
        "llm_raw_content": None,
        "llm_output_valid": None,
        "llm_parse_error": None,
        "llm_fallback_used": None,
        "llm_decision_raw": None,
        "pre_search_path": "deterministic_ask",
        "deterministic_reason": "exact_family_missing_field",
        "missing_fields": ["side"],
        "next_question_key": "side",
    }


@pytest.mark.parametrize(
    "message",
    [
        "rdiador gol 2010",
        "radiador gol 2010 vazando",
        "quero falar com um vendedor",
        "codigo AB-1234",
    ],
)
def test_deterministic_ask_returns_none_and_clears_audit_when_ineligible(
    message: str,
) -> None:
    validator = _validator()
    assert validator.try_validate_deterministic_ask("radiador gol 2010") is not None
    assert validator.get_last_audit() is not None

    result = validator.try_validate_deterministic_ask(message)

    assert result is None
    assert validator.get_last_audit() is None


def test_llm_validator_keeps_position_separate_from_axle_requirement() -> None:
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

    assert result.decision == "ask"
    assert result.missing_fields == ["axle"]
    assert result.next_question is not None
    assert result.next_question.key == "axle"
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
        needs_position=_catalog_fixture().needs_position - {"coxim"},
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


def test_llm_validator_uses_direction_answer_for_the_active_axle_question() -> None:
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
    assert str(result.criteria.vehicle_model).lower() == "ecosport"
    assert result.criteria.vehicle_year == 2008
    assert result.criteria.axle == "front"
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
    assert result.next_question.key == "axle"
    assert result.missing_fields == ["axle"]


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
    assert result.missing_fields == ["vehicle_year", "position"]


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
    assert result.criteria.part_query == "pastilhas de freio"
    assert result.criteria.position == "front"


def test_llm_validator_canonicalizes_singular_brake_disc_before_applying_rules() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"disco de freio","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("disco de freio gol 2010")

    assert result.decision == "ask"
    assert result.criteria.part_query == "discos de freio"
    assert result.next_question is not None
    assert result.next_question.key == "position"
    assert result.missing_fields == ["position"]


def test_llm_validator_asks_position_for_suspension_typo_alias() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":null,"vehicle_model":"EcoSport","vehicle_year":2008,"engine":"1.6"},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("voces tem a suspencao da ecosport 2008 1.6?")

    assert result.decision == "ask"
    assert result.criteria.part_query == "amortecedores suspensao"
    assert str(result.criteria.vehicle_model).lower() == "ecosport"
    assert result.criteria.vehicle_year == 2008
    assert result.criteria.engine == "1.6"
    assert result.next_question is not None
    assert result.next_question.key == "position"
    assert result.missing_fields == ["position"]


def test_llm_validator_handoffs_non_catalog_part_query() -> None:
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

    assert result.decision == "handoff"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "handoff"
    assert "catalogo" in result.next_question.prompt
    assert result.missing_fields == []


def test_llm_validator_handoffs_when_user_informed_non_catalog_part_but_llm_returns_null() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":null,"vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":["part_query"],'
                    '"next_question":{"type":"request_info","key":"part_query","prompt":"Qual peca voce precisa?"},'
                    '"confidence":0.7}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("farol gol 2010")

    assert result.decision == "handoff"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "handoff"
    assert result.missing_fields == []


def test_llm_validator_handoffs_farol_as_non_catalog_part_query() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"farol","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("farol gol 2010")

    assert result.decision == "handoff"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "handoff"
    assert result.missing_fields == []


def test_llm_validator_asks_for_specific_part_when_user_informs_known_group() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"part_query":null,"vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":["part_query"],'
                    '"next_question":{"type":"request_info","key":"part_query","prompt":"Qual item de freio voce precisa?"},'
                    '"confidence":0.7}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("voces tem freio do gol 2010?")

    assert result.decision == "ask"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "part_query"
    assert result.missing_fields == ["part_query"]


def test_llm_validator_does_not_handoff_when_llm_returns_known_group_as_part_query() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"search","criteria":{"part_query":"freio","vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":[],"next_question":null,"confidence":0.9}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("freio gol 2010")

    assert result.decision == "ask"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "part_query"
    assert result.missing_fields == ["part_query"]


def test_llm_validator_still_asks_for_part_when_user_did_not_inform_one() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {
            "message": {
                "content": (
                    '{"decision":"ask","criteria":{"vehicle_model":"Gol","vehicle_year":2010},'
                    '"missing_fields":["part_query"],'
                    '"next_question":{"type":"request_info","key":"part_query","prompt":"Qual peca voce precisa?"},'
                    '"confidence":0.7}'
                )
            }
        },
        "/api/chat",
    )

    result = validator.validate("bom dia tenho um gol 2010")

    assert result.decision == "ask"
    assert result.criteria.part_query is None
    assert result.next_question is not None
    assert result.next_question.key == "part_query"
    assert result.missing_fields == ["part_query"]


def test_llm_validator_canonicalizes_conversation_state_part_query_before_score_policy() -> None:
    validator = _validator()
    captured: dict[str, object] = {}

    def _fake_post_chat_or_generate(**kwargs):
        captured["dictionary_seed_criteria"] = kwargs["dictionary_seed_criteria"]
        captured["payload"] = kwargs["payload"]
        return (
            {
                "message": {
                    "content": (
                        '{"decision":"search","criteria":{"position":"dianteira"},'
                        '"missing_fields":[],"next_question":null,"confidence":0.9}'
                    )
                }
            },
            "/api/chat",
        )

    validator._post_chat_or_generate = _fake_post_chat_or_generate

    result = validator.validate(
        "dianteira",
        conversation_state=ConversationState(
            criteria=SearchCriteria(
                part_query="disco de freio",
                vehicle_model="Gol",
                vehicle_year=2010,
            ),
            pending_slot="position",
            pending_question="Em qual posicao a peca fica?",
            last_decision="ask",
        ),
    )

    dictionary_seed = captured["dictionary_seed_criteria"]
    assert isinstance(dictionary_seed, SearchCriteria)
    assert dictionary_seed.part_query == "discos de freio"
    assert result.decision == "search"
    assert result.criteria.part_query == "discos de freio"
    assert result.criteria.position == "front"


def test_llm_validator_chat_payload_includes_keep_alive() -> None:
    validator = _validator()

    payload = validator._build_chat_payload(
        message_text="coxim ecosport 2008",
        last_messages=[],
        dictionary_seed_criteria=SearchCriteria(part_query="coxim", vehicle_model="EcoSport", vehicle_year=2008),
        conversation_state=None,
    )

    assert payload["keep_alive"] == "1h"


def test_llm_residual_payload_separates_user_evidence_from_assistant_context() -> None:
    validator = _validator()
    state = ConversationState(
        criteria=SearchCriteria(part_query="radiador", vehicle_model="Gol", vehicle_year=2010),
        pending_slot="engine",
        pending_question="Qual a motorizacao do veiculo?",
        last_decision="ask",
    )
    payload = validator._build_chat_payload(
        message_text="na verdade e Corsa 2011",
        last_messages=[
            {"role": "user", "text": "quero radiador Gol 2010"},
            {"role": "assistant", "text": "Posso usar o Gol 2010"},
        ],
        dictionary_seed_criteria=SearchCriteria(vehicle_model="Corsa", vehicle_year=2011),
        conversation_state=state,
    )
    content = payload["messages"][1]["content"]
    user_input = json.loads(content)

    assert user_input["residual_only"] is True
    assert user_input["evidence_precedence"] == [
        "current_user_message",
        "current_message_dictionary_seed",
        "active_conversation_state_for_omitted_fields",
        "previous_user_messages_for_omitted_fields",
        "assistant_messages_context_only",
    ]
    assert user_input["previous_user_messages"] == [{"role": "user", "text": "quero radiador Gol 2010"}]
    assert user_input["assistant_context"] == [{"role": "assistant", "text": "Posso usar o Gol 2010"}]


def test_llm_validator_replaces_directional_question_with_public_vocabulary() -> None:
    validator = _validator()
    validator._post_chat_or_generate = lambda **kwargs: (
        {"message": {"content": (
            '{"decision":"ask","criteria":{"part_query":"bandeja","vehicle_model":"Gol","vehicle_year":2010},'
            '"missing_fields":["side"],'
            '"next_question":{"type":"request_info","key":"side","prompt":"Qual lateral?","options":["L","R"]},'
            '"confidence":0.8}'
        )}},
        "/api/chat",
    )

    result = validator.validate("bandeja Gol 2010")

    assert result.next_question is not None
    assert result.next_question.prompt == "Esquerdo ou direito?"
    assert result.next_question.options == ["Esquerdo", "Direito", "Nao sei"]


def test_default_directional_questions_keep_position_and_axle_distinct() -> None:
    validator = _validator()
    criteria = SearchCriteria(part_query="discos de freio", vehicle_model="Gol", vehicle_year=2010)

    position = validator._build_default_next_question(criteria=criteria, missing_fields=["position"])
    axle = validator._build_default_next_question(criteria=criteria, missing_fields=["axle"])

    assert position is not None and position.prompt == "Dianteiro ou traseiro?"
    assert axle is not None and axle.prompt == "Eixo dianteiro ou traseiro?"


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
