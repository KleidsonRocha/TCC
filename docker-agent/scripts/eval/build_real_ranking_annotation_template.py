"""Build a human ERP annotation scaffold from a real-response execution JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_template(run_rows: list[dict[str, Any]], source_name: str) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for row in run_rows:
        search_items = (row.get("search_diagnostics") or {}).get("items") or []
        for item_index, item in enumerate(search_items):
            cases.append({
                "scenario_id": row["scenario_id"],
                "turn_id": row["turn_id"],
                "item_index": item_index,
                "tier": row.get("tier"),
                "category": row.get("category"),
                "request_text": (row.get("request") or {}).get("text", ""),
                "criteria_to_verify": item.get("criteria") or {},
                "evaluable": False,
                "expected_no_match": None,
                "compatible_item_ids": [],
                "preferred_or_confirmed_item_ids": [],
                "incompatible_item_ids": [],
                "acceptable_tie_groups": [],
                "notes": "",
                "review_status": "pending",
                "reviewer": None,
                "reviewed_at": None,
            })
    return {
        "name": "real_respond_ranking_annotations",
        "schema_version": "1.0",
        "status": "annotation_template",
        "source_dataset": "battery_real_omnichannel_250.json",
        "template_run": source_name,
        "annotation_policy": {
            "independent_of_ai_output": True,
            "evaluable": "Set true only after ERP evidence is sufficient to judge this item query.",
            "expected_no_match": "true only after confirming no applicable ERP item; false when one or more compatible items exist.",
            "compatible_item_ids": "All technically compatible ERP item codes, not only the seller-selected code.",
            "preferred_or_confirmed_item_ids": "Seller-confirmed or specifically preferred item codes, when known.",
            "incompatible_item_ids": "Codes reviewed and confirmed incompatible; leave other candidates unlabeled.",
            "acceptable_tie_groups": "Groups of interchangeable codes; also list those codes as compatible.",
            "item_index": "Zero-based query index for multi-item turns.",
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="JSON written by run_real_respond_battery")
    parser.add_argument("--output", type=Path, default=Path(
        "docs/assets/datasets/real_respond_ranking_annotations_v1.json"
    ))
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"output already exists; choose a new path to avoid overwriting annotations: {args.output}")
    run_rows = json.loads(args.run.read_text(encoding="utf-8"))
    template = build_template(run_rows, args.run.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.output}: {len(template['cases'])} query annotations")


if __name__ == "__main__":
    main()
