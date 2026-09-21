"""Evaluate every seeded part alias against the runtime deterministic catalog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.config import Settings
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from scripts.eval.build_part_family_coverage_dataset import DEFAULT_OUTPUT_DIR, build_documents


class _NullLogger:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None

    def exception(self, *args: Any, **kwargs: Any) -> None:
        return None


def evaluate(*, progress_every: int = 250) -> dict[str, Any]:
    coverage, _ = build_documents()
    catalog = resolve_pre_search_catalog(settings=Settings(), logger=_NullLogger())
    extractor = DictionaryPreSearchExtractor(catalog=catalog)
    safe_total = safe_passed = 0
    missing_seed_total = missing_seed_passed = 0
    ambiguous_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    cases = coverage["cases"]
    for index, case in enumerate(cases, start=1):
        actual = extractor.extract(case["message"]).part_query
        expected = case["expected_part_families"]
        if case["ambiguous"]:
            ambiguous_rows.append({
                "id": case["id"], "message": case["message"],
                "expected_part_families": expected, "actual_part_family": actual,
            })
            continue
        safe_total += 1
        if case["source"] == "canonical_without_seeded_alias":
            missing_seed_total += 1
        if actual == expected[0]:
            safe_passed += 1
            if case["source"] == "canonical_without_seeded_alias":
                missing_seed_passed += 1
        else:
            failures.append({
                "id": case["id"], "message": case["message"],
                "expected_part_family": expected[0], "actual_part_family": actual,
            })
        if progress_every and (index % progress_every == 0 or index == len(cases)):
            print(
                json.dumps(
                    {"progress": f"{index}/{len(cases)}", "failures": len(failures)},
                    ensure_ascii=False,
                ),
                flush=True,
            )

    return {
        "schema_version": "1.0",
        "part_types_total": coverage["part_types_total"],
        "part_types_with_aliases": coverage["part_types_with_aliases"],
        "part_types_without_aliases": coverage["part_types_without_aliases"],
        "families_total": coverage["families_total"],
        "families_with_aliases": coverage["families_with_aliases"],
        "aliases_total": coverage["aliases_total"],
        "safe_cases_total": safe_total,
        "safe_cases_passed": safe_passed,
        "safe_cases_failed": len(failures),
        "safe_coverage_pct": round((safe_passed / safe_total) * 100, 2) if safe_total else 100.0,
        "ambiguous_cases_excluded": len(ambiguous_rows),
        "missing_seed_cases_total": missing_seed_total,
        "missing_seed_cases_passed": missing_seed_passed,
        "ambiguous_actual_counts": dict(Counter(str(row["actual_part_family"]) for row in ambiguous_rows)),
        "failures": failures,
        "ambiguous_cases": ambiguous_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR / "part_alias_coverage_report.json")
    parser.add_argument("--progress-every", type=int, default=250)
    args = parser.parse_args()
    report = evaluate(progress_every=args.progress_every)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"failures", "ambiguous_cases"}}, ensure_ascii=False))
    print(f"report={args.output}")
    # Missing aliases are a catalog-data backlog, shown separately.  Only a
    # regression in a currently seeded, unambiguous alias fails this command.
    seeded_failures = [
        row for row in report["failures"]
        if not row["id"].startswith("missing-alias-")
    ]
    if seeded_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
