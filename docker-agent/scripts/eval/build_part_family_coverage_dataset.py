"""Generate deterministic alias coverage and one residual-LLM case per part family."""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / ".tmp" / "eval" / "part_family_coverage"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(value.casefold().split())


def load_rows() -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], bool], list[dict[str, str]]]:
    csv_dir = ROOT / "db" / "init" / "csv"
    with (csv_dir / "subgrupo.csv").open(encoding="utf-8-sig", newline="") as source:
        names = {
            (row["cd_grupo"], row["cd_subgrupo"]): normalize(row["nm_subgrupo"])
            for row in csv.DictReader(source)
        }
    with (csv_dir / "pre_search_part_rule.csv").open(encoding="utf-8-sig", newline="") as source:
        generic = {
            (row["cd_grupo"], row["part_type_id"]): row["is_generic"].strip().casefold() == "true"
            for row in csv.DictReader(source, delimiter=";")
        }
    with (csv_dir / "pre_search_part_alias.csv").open(encoding="utf-8-sig", newline="") as source:
        aliases = list(csv.DictReader(source))
    return names, generic, aliases


def build_documents() -> tuple[dict, list[dict]]:
    names, generic, aliases = load_rows()
    alias_targets: dict[str, set[str]] = defaultdict(set)
    aliases_by_family: dict[str, set[str]] = defaultdict(set)
    type_keys_with_aliases: set[tuple[str, str]] = set()
    for row in aliases:
        key = (row["cd_grupo"], row["cd_subgrupo"])
        family = names[key]
        alias = normalize(row["alias"])
        alias_targets[alias].add(family)
        aliases_by_family[family].add(alias)
        type_keys_with_aliases.add(key)

    all_families = set(names.values())
    types_without_aliases = sorted(set(names) - type_keys_with_aliases)

    coverage_cases: list[dict] = []
    for alias, targets in sorted(alias_targets.items()):
        variants = [alias, f"quero {alias}", f"preciso de {alias}"]
        for message in variants:
            coverage_cases.append({
                "id": f"alias-{len(coverage_cases) + 1:05d}",
                "message": message,
                "expected_part_families": sorted(targets),
                "ambiguous": len(targets) > 1,
                "source": "seeded_alias",
            })

    # These rows intentionally reveal catalog bootstrap gaps.  We do not
    # invent aliases: the report must show that the runtime cannot yet
    # recognize this catalog family until its alias is seeded and committed.
    for key in types_without_aliases:
        family = names[key]
        for message in (family, f"quero {family}", f"preciso de {family}"):
            coverage_cases.append({
                "id": f"missing-alias-{len(coverage_cases) + 1:05d}",
                "message": message,
                "expected_part_families": [family],
                "ambiguous": False,
                "source": "canonical_without_seeded_alias",
            })

    llm_cases: list[dict] = []
    llm_excluded_families: list[str] = []
    for family, aliases_for_family in sorted(aliases_by_family.items()):
        # A label shared by two catalog families has no single correct intent
        # without further vehicle or product context.  It belongs to the
        # ambiguity report, never to an LLM golden with a fabricated answer.
        representative = next(
            (
                item
                for item in sorted(aliases_for_family)
                if item != family and alias_targets[item] == {family}
            ),
            None,
        )
        family_keys = [key for key, name in names.items() if name == family]
        is_generic = any(generic.get(key, False) for key in family_keys)
        if is_generic or representative is None:
            llm_excluded_families.append(family)
            continue
        llm_cases.append({
            "id": f"family-{len(llm_cases) + 1:03d}",
            "message.text": f"quero {representative}",
            "context.last_messages": [],
            "expected": {
                "decision": "ask",
                "criteria": {"part_query": family},
                "missing_fields_contains": ["vehicle_model"],
                "next_question_key": "vehicle_model",
            },
            "metadata": {"representative_alias": representative, "source": "catalog_seed"},
        })

    return {
        "schema_version": "1.0",
        "part_types_total": len(names),
        "part_types_with_aliases": len(type_keys_with_aliases),
        "part_types_without_aliases": [
            {"source_group_code": key[0], "source_subgroup_code": key[1], "part_family": names[key]}
            for key in types_without_aliases
        ],
        # Some ERP subgroups share a normalized family name.  The runtime
        # routes by this canonical family, so retain both counts in reports.
        "families_total": len(all_families),
        "families_with_aliases": len(aliases_by_family),
        "aliases_total": len(alias_targets),
        "ambiguous_aliases_total": sum(len(targets) > 1 for targets in alias_targets.values()),
        "llm_excluded_families": llm_excluded_families,
        "cases": coverage_cases,
    }, llm_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    coverage, llm_cases = build_documents()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = args.output_dir / "part_alias_coverage.json"
    llm_path = args.output_dir / "part_family_llm_golden.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    llm_path.write_text(json.dumps(llm_cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": str(coverage_path), "llm_golden": str(llm_path), **{k: coverage[k] for k in ("part_types_total", "part_types_with_aliases", "families_total", "aliases_total", "ambiguous_aliases_total")}, "coverage_cases": len(coverage["cases"]), "llm_cases": len(llm_cases)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
