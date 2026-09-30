import csv
import unicodedata
from pathlib import Path

import pytest


CATALOG_CSV_DIR = Path("db/init/csv")
PART_RULE_PATH = CATALOG_CSV_DIR / "pre_search_part_rule.csv"
SUBGROUP_PATH = CATALOG_CSV_DIR / "subgrupo.csv"
PART_ALIAS_PATH = CATALOG_CSV_DIR / "pre_search_part_alias.csv"

AUDITED_FILTER_FAMILIES = {
    "filtro de ar condicionado",
    "filtro de ar do motor",
    "filtro de cabine",
    "filtro de combustivel",
    "filtro de oleo",
    "filtro de cambio",
    "mangueiras de filtro de ar",
    "pre filtro injecao",
}

NON_DIRECTIONAL_RULE_EXPECTATIONS = (
    ("aditivos", "needs_side"),
    ("anti-chama", "needs_axle"),
    ("bico injetor", "needs_side"),
    ("lubrificantes", "needs_axle"),
    ("velas de ignicao automotivas", "needs_side"),
    ("bieletas", "needs_side"),
    ("atuador de embreagem", "needs_side"),
)

REQUIRED_RULE_EXPECTATIONS = (
    ("coxins", "needs_position"),
    ("lubrificantes", "needs_variant"),
    ("pastilhas de freio", "needs_position"),
    ("batentes", "needs_position"),
)

NON_REQUIRED_RULE_EXPECTATIONS = (
    ("coxins", "needs_axle"),
    ("pastilhas de freio", "needs_engine"),
    ("batentes", "needs_side"),
    ("batentes", "needs_axle"),
)


def _load_subgroups() -> dict[tuple[str, str], str]:
    with SUBGROUP_PATH.open(encoding="utf-8", newline="") as file:
        return {
            (row["cd_grupo"], row["cd_subgrupo"]): row["nm_subgrupo"]
            for row in csv.DictReader(file)
        }


def _load_rules_by_family() -> dict[str, list[dict[str, str]]]:
    subgroups = _load_subgroups()
    with PART_RULE_PATH.open(encoding="utf-8", newline="") as file:
        rules = list(csv.DictReader(file, delimiter=";"))

    rules_by_family: dict[str, list[dict[str, str]]] = {}
    for rule in rules:
        key = (rule["cd_grupo"], rule["part_type_id"])
        family = _normalize_family(subgroups[key])
        rules_by_family.setdefault(family, []).append(rule)
    return rules_by_family


def _normalize_family(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().lower())
    return "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )


def _as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def test_filter_family_audit_covers_every_current_catalog_family() -> None:
    filter_families = {
        normalized
        for family in _load_subgroups().values()
        if "filtro" in (normalized := _normalize_family(family))
    }

    assert filter_families == AUDITED_FILTER_FAMILIES


@pytest.mark.parametrize("family", sorted(AUDITED_FILTER_FAMILIES))
def test_filter_families_do_not_require_directional_slots(family: str) -> None:
    matching_rules = _load_rules_by_family()[family]
    assert len(matching_rules) == 1, family
    rule = matching_rules[0]

    assert not _as_bool(rule["needs_side"]), family
    assert not _as_bool(rule["needs_position"]), family
    assert not _as_bool(rule["needs_axle"]), family


@pytest.mark.parametrize(("family", "field"), NON_DIRECTIONAL_RULE_EXPECTATIONS)
def test_audited_engine_product_families_do_not_require_directional_slots(
    family: str,
    field: str,
) -> None:
    matching_rules = _load_rules_by_family()[family]
    assert matching_rules, family

    for rule in matching_rules:
        assert not _as_bool(rule[field]), f"{family}: {field}"


@pytest.mark.parametrize(("family", "field"), REQUIRED_RULE_EXPECTATIONS)
def test_audited_families_require_their_search_discriminator(
    family: str,
    field: str,
) -> None:
    matching_rules = _load_rules_by_family()[family]
    assert matching_rules, family

    for rule in matching_rules:
        assert _as_bool(rule[field]), f"{family}: {field}"


@pytest.mark.parametrize(("family", "field"), NON_REQUIRED_RULE_EXPECTATIONS)
def test_audited_families_do_not_require_an_unsupported_discriminator(
    family: str,
    field: str,
) -> None:
    matching_rules = _load_rules_by_family()[family]
    assert matching_rules, family

    for rule in matching_rules:
        assert not _as_bool(rule[field]), f"{family}: {field}"


def test_batente_aliases_include_the_suspension_subgroup() -> None:
    with PART_ALIAS_PATH.open(encoding="utf-8", newline="") as file:
        aliases = {
            (row["cd_grupo"], row["cd_subgrupo"], row["alias"])
            for row in csv.DictReader(file)
        }

    assert ("2", "5", "batente") in aliases
    assert ("2", "5", "batentes") in aliases


def test_cruzeta_singular_maps_to_cardan_cross_joint_family() -> None:
    with PART_ALIAS_PATH.open(encoding="utf-8", newline="") as file:
        aliases = {
            (row["cd_grupo"], row["cd_subgrupo"], row["alias"])
            for row in csv.DictReader(file)
        }
    assert ("6", "7", "cruzeta") in aliases


def test_curated_erp_scopes_cover_observed_misclassified_candidates() -> None:
    sql = Path("db/init/pre_search_init.sql").read_text(encoding="utf-8")
    assert "('batentes', 2, 6, 'seed_csv')" in sql
    assert "('atuador de embreagem', 10, 5, 'seed_csv')" in sql
    assert "('eletroventilador', 9, 27, 'seed_csv')" in sql
