"""Score a real-response battery against manually reviewed ERP annotations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ANNOTATIONS = Path("docs/assets/datasets/real_respond_ranking_annotations_v1.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(record: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(record.get("scenario_id", "")),
        str(record.get("turn_id", "")),
        int(record.get("item_index", 0)),
    )


def _ranked_ids(row: dict[str, Any], item_index: int) -> list[str]:
    diagnostics = row.get("search_diagnostics")
    diag_items = diagnostics.get("items", []) if isinstance(diagnostics, dict) else []
    if item_index < len(diag_items):
        item_diagnostics = diag_items[item_index].get("diagnostics", {})
        ranked = item_diagnostics.get("ranked_candidates", [])
        if ranked:
            ranked = sorted(ranked, key=lambda item: int(item.get("rank_position", 10**9)))
            return [str(item["item_id"]) for item in ranked if item.get("item_id") is not None]

    if item_index == 0:
        summary = row.get("summary", {})
        candidates = summary.get("catalog_candidates", []) if isinstance(summary, dict) else []
        if candidates:
            candidates = sorted(candidates, key=lambda item: int(item.get("position", 10**9)))
            return [str(item["item_id"]) for item in candidates if item.get("item_id") is not None]
    return []


def _percent(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def calculate_metrics(run_rows: list[dict[str, Any]], annotations: dict[str, Any]) -> dict[str, Any]:
    run_index: dict[tuple[str, str], dict[str, Any]] = {
        (str(row.get("scenario_id", "")), str(row.get("turn_id", ""))): row
        for row in run_rows
    }
    cases = annotations.get("cases", [])
    pending = sum(case.get("evaluable") is not True for case in cases)
    ranked_cases: list[tuple[dict[str, Any], list[str]]] = []
    no_match_counts = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    incompatible = known_top3 = preferred_top1 = preferred_denominator = 0
    missing_run_cases = 0

    for case in cases:
        if case.get("evaluable") is not True:
            continue
        expected_no_match = case.get("expected_no_match")
        compatible_ids = case.get("compatible_item_ids", [])
        if not isinstance(expected_no_match, bool):
            raise ValueError(f"evaluable case {_key(case)} must set expected_no_match to true or false")
        if expected_no_match is False and not compatible_ids:
            raise ValueError(f"positive case {_key(case)} must list compatible_item_ids")
        if expected_no_match is True and compatible_ids:
            raise ValueError(f"no-match case {_key(case)} cannot list compatible_item_ids")
        scenario_id, turn_id, item_index = _key(case)
        row = run_index.get((scenario_id, turn_id))
        if row is None:
            missing_run_cases += 1
            continue
        predicted = _ranked_ids(row, item_index)
        diag = row.get("search_diagnostics") or {}
        diag_items = diag.get("items") or []
        search_was_captured = (
            diag.get("capture_status") == "captured" and item_index < len(diag_items)
        )
        if isinstance(expected_no_match, bool) and search_was_captured:
            predicted_no_match = not predicted
            if expected_no_match and predicted_no_match:
                no_match_counts["TP"] += 1
            elif expected_no_match and not predicted_no_match:
                no_match_counts["FN"] += 1
            elif not expected_no_match and predicted_no_match:
                no_match_counts["FP"] += 1
            else:
                no_match_counts["TN"] += 1

        compatible = {str(item) for item in case.get("compatible_item_ids", [])}
        if expected_no_match is False and compatible:
            ranked_cases.append((case, predicted))
            incompat_ids = {str(item) for item in case.get("incompatible_item_ids", [])}
            known = compatible | incompat_ids
            for item_id in predicted[:3]:
                if item_id in known:
                    known_top3 += 1
                    incompatible += item_id in incompat_ids

        preferred = {str(item) for item in case.get("preferred_or_confirmed_item_ids", [])}
        if preferred:
            preferred_denominator += 1
            acceptable = set(preferred)
            for group in case.get("acceptable_tie_groups", []):
                group_ids = {str(item) for item in group}
                if group_ids & preferred:
                    acceptable.update(group_ids)
            preferred_top1 += bool(predicted and predicted[0] in acceptable)

    top1_hits = sum(bool(ids and ids[0] in {str(x) for x in case["compatible_item_ids"]})
                    for case, ids in ranked_cases)
    top3_hits = sum(bool(set(ids[:3]) & {str(x) for x in case["compatible_item_ids"]})
                    for case, ids in ranked_cases)
    denominator = len(ranked_cases)
    no_match_precision_denom = no_match_counts["TP"] + no_match_counts["FP"]
    no_match_recall_denom = no_match_counts["TP"] + no_match_counts["FN"]

    return {
        "evaluated_positive_cases": denominator,
        "pending_cases": pending,
        "missing_run_cases": missing_run_cases,
        "top1_hits": top1_hits,
        "top1_denominator": denominator,
        "top3_hits": top3_hits,
        "top3_denominator": denominator,
        "preferred_top1_hits": preferred_top1,
        "preferred_top1_denominator": preferred_denominator,
        "incompatible_top3": incompatible,
        "known_top3_denominator": known_top3,
        "no_match_counts": no_match_counts,
        "no_match_precision_denominator": no_match_precision_denom,
        "no_match_recall_denominator": no_match_recall_denom,
    }


def render_report(metrics: dict[str, Any], run_name: str) -> str:
    no_match_counts = metrics["no_match_counts"]
    lines = [
        "# Avaliação de ranking real",
        "",
        f"Execução: `{run_name}`",
        f"Rótulos avaliáveis: {metrics['evaluated_positive_cases']}; pendentes/não avaliáveis: {metrics['pending_cases']}; sem execução correspondente: {metrics['missing_run_cases']}.",
        "",
        "| Métrica | Resultado |",
        "|---|---:|",
        f"| Compatibilidade Top-1 | {metrics['top1_hits']}/{metrics['top1_denominator']} ({_percent(metrics['top1_hits'], metrics['top1_denominator'])}) |",
        f"| Compatibilidade Top-3 | {metrics['top3_hits']}/{metrics['top3_denominator']} ({_percent(metrics['top3_hits'], metrics['top3_denominator'])}) |",
        f"| Preferido/confirmado Top-1, aceitando grupos de empate | {metrics['preferred_top1_hits']}/{metrics['preferred_top1_denominator']} ({_percent(metrics['preferred_top1_hits'], metrics['preferred_top1_denominator'])}) |",
        f"| Candidatos incompatíveis entre posições Top-3 rotuladas | {metrics['incompatible_top3']}/{metrics['known_top3_denominator']} ({_percent(metrics['incompatible_top3'], metrics['known_top3_denominator'])}) |",
        "",
        "## No-match",
        "",
        f"TP={no_match_counts['TP']}, FP={no_match_counts['FP']}, FN={no_match_counts['FN']}, TN={no_match_counts['TN']}",
        f"Precisão={_percent(no_match_counts['TP'], metrics['no_match_precision_denominator'])}; recall={_percent(no_match_counts['TP'], metrics['no_match_recall_denominator'])}.",
        "",
        "Top-1/Top-3 contam como acerto quando o código retornado pertence a `compatible_item_ids`. `preferred_or_confirmed_item_ids` mede separadamente a preferência/seleção comercial. Grupos de empate só ampliam essa segunda métrica; eles não tornam um código compatível sem anotação explícita.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, help="JSON de execução do run_real_respond_battery")
    parser.add_argument("--compare-run", type=Path, help="Outra execução avaliada com as mesmas anotações")
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--output", type=Path, help="Markdown de saída; por padrão imprime no terminal")
    args = parser.parse_args()

    annotations = _load_json(args.annotations)
    current_rows = _load_json(args.run)
    current_metrics = calculate_metrics(current_rows, annotations)
    report = render_report(current_metrics, args.run.name)
    if args.compare_run:
        comparison_rows = _load_json(args.compare_run)
        current_keys = {
            (str(row.get("scenario_id", "")), str(row.get("turn_id", "")))
            for row in current_rows
        }
        comparison_keys = {
            (str(row.get("scenario_id", "")), str(row.get("turn_id", "")))
            for row in comparison_rows
        }
        common_keys = current_keys & comparison_keys
        paired_annotations = {
            **annotations,
            "cases": [
                case for case in annotations.get("cases", [])
                if (str(case.get("scenario_id", "")), str(case.get("turn_id", ""))) in common_keys
            ],
        }
        current_paired = calculate_metrics(current_rows, paired_annotations)
        comparison_paired = calculate_metrics(comparison_rows, paired_annotations)
        changes = []
        for label, key in (("Top-1 compatível", "top1"), ("Top-3 compatível", "top3")):
            base_hits = comparison_paired[f"{key}_hits"]
            base_den = comparison_paired[f"{key}_denominator"]
            current_hits = current_paired[f"{key}_hits"]
            current_den = current_paired[f"{key}_denominator"]
            base_rate = base_hits / base_den if base_den else None
            current_rate = current_hits / current_den if current_den else None
            if base_rate is None or current_rate is None:
                delta = "n/a"
            else:
                delta = f"{(current_rate - base_rate) * 100:+.1f} p.p."
            changes.append(
                f"| {label} | {base_hits}/{base_den} ({_percent(base_hits, base_den)}) "
                f"| {current_hits}/{current_den} ({_percent(current_hits, current_den)}) | {delta} |"
            )
        report += (
            "\n\n## Comparação pareada\n\n"
            f"Base: `{args.compare_run.name}`; atual: `{args.run.name}`; "
            f"casos com chave nos dois runs: {len(paired_annotations['cases'])}.\n\n"
            "| Métrica | Base | Atual | Variação |\n|---|---:|---:|---:|\n"
            + "\n".join(changes)
            + "\n"
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(report)


if __name__ == "__main__":
    main()
