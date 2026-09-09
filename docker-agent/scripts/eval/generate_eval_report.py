import argparse
import json
import sys
from pathlib import Path
from typing import Any, TypeVar

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import Settings
from app.infra.logger import configure_logging, get_logger
from app.infra.pre_search_benchmark import (
    as_context,
    benchmark_model,
    load_dataset,
    make_validator,
    pick_recommendation,
    values_match,
)


DEFAULT_MVP_DATASET = Path("docs/assets/datasets/pre_search_eval_dataset_mvp.json")
DEFAULT_GOLDEN_DATASET = Path("docs/assets/datasets/pre_search_num_predict_golden_set.json")
DEFAULT_REAL_BATTERY_JSON = Path("docs/assets/reports/real_respond_battery_2026-03-25.json")
DEFAULT_OUTPUT_JSON = Path("docs/assets/reports/eval_report.json")
DEFAULT_OUTPUT_MD = Path("docs/assets/reports/eval_report.md")
T = TypeVar("T")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _percent(ok: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((ok / total) * 100, 2)


def _slice_rows(rows: list[T], limit: int | None) -> list[T]:
    if limit is None or limit <= 0:
        return rows
    return rows[:limit]


def run_mvp_eval(*, settings: Settings, dataset_path: Path, limit: int | None = None) -> dict[str, Any]:
    validator = make_validator(settings=settings, logger=get_logger("eval-report"))
    rows = _slice_rows(_load_json(dataset_path), limit)

    decision_ok = 0
    next_question_ok = 0
    next_question_total = 0
    slot_total = 0
    slot_ok = 0
    slots = (
        "part_query",
        "preferred_product_brand",
        "vehicle_brand",
        "vehicle_model",
        "vehicle_year",
        "engine",
        "side",
        "position",
        "axle",
        "variant",
        "quantity",
    )
    cases: list[dict[str, Any]] = []

    for row in rows:
        message = str(row.get("message.text", ""))
        context = as_context(row.get("context.last_messages", []))
        expected = row.get("expected", {})
        result = validator.validate(message_text=message, last_messages=context)

        case_record = {
            "message_text": message,
            "expected_decision": expected.get("decision"),
            "actual_decision": result.decision,
            "criteria_failures": [],
            "next_question_expected_key": None,
            "next_question_actual_key": result.next_question.key if result.next_question else None,
        }

        if result.decision == expected.get("decision"):
            decision_ok += 1

        expected_q = expected.get("next_question")
        if expected_q:
            next_question_total += 1
            case_record["next_question_expected_key"] = expected_q.get("key")
            predicted_key = result.next_question.key if result.next_question else None
            if predicted_key == expected_q.get("key"):
                next_question_ok += 1

        expected_criteria = expected.get("criteria", {})
        for slot in slots:
            if slot not in expected_criteria:
                continue
            slot_total += 1
            predicted_value = getattr(result.criteria, slot, None)
            expected_value = expected_criteria.get(slot)
            if values_match(predicted_value, expected_value):
                slot_ok += 1
            else:
                case_record["criteria_failures"].append(
                    {
                        "slot": slot,
                        "expected": expected_value,
                        "actual": predicted_value,
                    }
                )

        cases.append(case_record)

    failed_cases = [
        case for case in cases
        if case["expected_decision"] != case["actual_decision"] or case["criteria_failures"]
    ]
    return {
        "dataset": str(dataset_path).replace("\\", "/"),
        "dataset_size": len(rows),
        "decision_accuracy_pct": _percent(decision_ok, len(rows)),
        "slot_extraction_accuracy_pct": _percent(slot_ok, slot_total),
        "next_question_utility_pct": _percent(next_question_ok, next_question_total),
        "failed_cases": failed_cases[:10],
    }


def run_golden_benchmark(
    *,
    settings: Settings,
    dataset_path: Path,
    num_predict: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    dataset = _slice_rows(load_dataset(dataset_path), limit)
    return benchmark_model(
        dataset=dataset,
        settings=settings,
        num_predict=num_predict,
    )


def run_num_predict_sweep(
    *,
    settings: Settings,
    dataset_path: Path,
    values: list[int],
    limit: int | None = None,
) -> dict[str, Any]:
    dataset = _slice_rows(load_dataset(dataset_path), limit)
    results = [
        benchmark_model(dataset=dataset, settings=settings, num_predict=value)
        for value in values
    ]
    recommendation = pick_recommendation(results)
    return {
        "dataset": str(dataset_path).replace("\\", "/"),
        "values": values,
        "recommendation": recommendation,
        "results": results,
    }


def summarize_real_battery(path: Path) -> dict[str, Any]:
    rows = _load_json(path)
    http_200 = sum(1 for row in rows if int(row.get("status_code", 0)) == 200)
    errors = len(rows) - http_200
    request_info = 0
    show_items = 0
    handoff = 0
    latencies: list[float] = []
    categories: dict[str, int] = {}

    for row in rows:
        latencies.append(float(row.get("elapsed_ms", 0.0)))
        category = str(row.get("category", "unknown"))
        categories[category] = categories.get(category, 0) + 1
        response = row.get("response", {}) if isinstance(row, dict) else {}
        actions = response.get("actions", []) if isinstance(response, dict) else []
        if any(action.get("type") == "request_info" for action in actions):
            request_info += 1
        if any(action.get("type") == "show_items" for action in actions):
            show_items += 1
        handoff_payload = response.get("handoff", {}) if isinstance(response, dict) else {}
        if handoff_payload.get("required"):
            handoff += 1

    interesting_cases = []
    for row in rows:
        summary = row.get("summary", {})
        if (
            int(row.get("status_code", 0)) != 200
            or summary.get("handoff_required")
            or summary.get("show_items_count", 0) > 0
        ):
            interesting_cases.append(
                {
                    "case_id": row.get("case_id"),
                    "category": row.get("category"),
                    "status_code": row.get("status_code"),
                    "elapsed_ms": row.get("elapsed_ms"),
                    "reply_text": summary.get("reply_text"),
                    "handoff_required": summary.get("handoff_required"),
                    "show_items_count": summary.get("show_items_count"),
                }
            )

    return {
        "path": str(path).replace("\\", "/"),
        "cases_total": len(rows),
        "http_200": http_200,
        "errors": errors,
        "request_info_cases": request_info,
        "show_items_cases": show_items,
        "handoff_cases": handoff,
        "latency_min_ms": round(min(latencies), 2) if latencies else 0.0,
        "latency_max_ms": round(max(latencies), 2) if latencies else 0.0,
        "latency_avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "categories": categories,
        "interesting_cases": interesting_cases[:15],
    }


def render_markdown(report: dict[str, Any]) -> str:
    settings = report["settings"]
    mvp = report.get("mvp_eval")
    golden = report.get("golden_benchmark")
    sweep = report.get("num_predict_sweep")
    real_battery = report.get("real_battery")

    lines: list[str] = []
    lines.append("# Relatorio Completo De Avaliacao")
    lines.append("")
    lines.append("## Escopo")
    lines.append("")
    lines.append("Este relatorio consolida os dois fluxos principais de avaliacao do projeto:")
    lines.append("")
    lines.append("- avaliacao offline do validador/LLM")
    lines.append("- bateria real do endpoint `/respond`")
    lines.append("")
    lines.append("## Configuracao")
    lines.append("")
    lines.append(f"- `llm_model`: `{settings['llm_model']}`")
    lines.append(f"- `llm_num_predict`: `{settings['llm_num_predict']}`")
    lines.append(f"- `llm_base_url`: `{settings['llm_base_url']}`")
    lines.append(f"- `catalog_db_enabled`: `{settings['catalog_db_enabled']}`")
    lines.append("")
    if mvp:
        lines.append("## MVP Offline")
        lines.append("")
        lines.append(f"- dataset: `{mvp['dataset']}`")
        lines.append(f"- dataset_size: `{mvp['dataset_size']}`")
        lines.append(f"- decision_accuracy_pct: `{mvp['decision_accuracy_pct']}`")
        lines.append(f"- slot_extraction_accuracy_pct: `{mvp['slot_extraction_accuracy_pct']}`")
        lines.append(f"- next_question_utility_pct: `{mvp['next_question_utility_pct']}`")
        if mvp["failed_cases"]:
            lines.append("- amostra de falhas:")
            for case in mvp["failed_cases"]:
                lines.append(
                    f"  - pergunta=`{case['message_text']}` | expected=`{case['expected_decision']}` | actual=`{case['actual_decision']}`"
                )
        lines.append("")
    if golden:
        lines.append("## Golden Benchmark")
        lines.append("")
        lines.append(f"- dataset: `{golden['dataset'] if 'dataset' in golden else report['golden_dataset']}`")
        lines.append(f"- cases_total: `{golden['cases_total']}`")
        lines.append(f"- case_pass_pct: `{golden['case_pass_pct']}`")
        lines.append(f"- decision_accuracy_pct: `{golden['decision_accuracy_pct']}`")
        lines.append(f"- criteria_accuracy_pct: `{golden['criteria_accuracy_pct']}`")
        lines.append(f"- missing_fields_accuracy_pct: `{golden['missing_fields_accuracy_pct']}`")
        lines.append(f"- next_question_key_accuracy_pct: `{golden['next_question_key_accuracy_pct']}`")
        lines.append(f"- latency_avg_ms: `{golden['latency_avg_ms']}`")
        lines.append(f"- latency_p50_ms: `{golden['latency_p50_ms']}`")
        lines.append(f"- latency_p95_ms: `{golden['latency_p95_ms']}`")
        lines.append("")
    if sweep:
        lines.append("## Num Predict Sweep")
        lines.append("")
        lines.append(f"- valores testados: `{sweep['values']}`")
        lines.append(f"- recomendacao: `num_predict={sweep['recommendation']['num_predict']}`")
        lines.append(f"- recommendation.case_pass_pct: `{sweep['recommendation']['case_pass_pct']}`")
        lines.append(f"- recommendation.decision_accuracy_pct: `{sweep['recommendation']['decision_accuracy_pct']}`")
        lines.append(f"- recommendation.latency_avg_ms: `{sweep['recommendation']['latency_avg_ms']}`")
        lines.append("")
    if real_battery:
        lines.append("## Bateria Real")
        lines.append("")
        lines.append(f"- origem: `{real_battery['path']}`")
        lines.append(f"- cases_total: `{real_battery['cases_total']}`")
        lines.append(f"- http_200: `{real_battery['http_200']}`")
        lines.append(f"- errors: `{real_battery['errors']}`")
        lines.append(f"- request_info_cases: `{real_battery['request_info_cases']}`")
        lines.append(f"- show_items_cases: `{real_battery['show_items_cases']}`")
        lines.append(f"- handoff_cases: `{real_battery['handoff_cases']}`")
        lines.append(f"- latency_avg_ms: `{real_battery['latency_avg_ms']}`")
        lines.append(f"- latency_max_ms: `{real_battery['latency_max_ms']}`")
        lines.append(f"- categories: `{real_battery['categories']}`")
        if real_battery["interesting_cases"]:
            lines.append("- amostra de casos:")
            for case in real_battery["interesting_cases"]:
                lines.append(
                    f"  - `{case['case_id']}` | `{case['category']}` | status=`{case['status_code']}` | handoff=`{case['handoff_required']}` | show_items=`{case['show_items_count']}`"
                )
        lines.append("")
    lines.append("## Operacao Recomendada")
    lines.append("")
    lines.append("Use apenas dois entrypoints operacionais em `scripts/eval/`:")
    lines.append("")
    lines.append("- `generate_eval_report.py` para consolidar avaliacao offline e, opcionalmente, resumir a bateria real")
    lines.append("- `run_real_respond_battery.py` para testar a API real e gerar evidencias de ponta a ponta")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera um relatorio consolidado de avaliacao do projeto.")
    parser.add_argument("--mvp-dataset", default=str(DEFAULT_MVP_DATASET))
    parser.add_argument("--golden-dataset", default=str(DEFAULT_GOLDEN_DATASET))
    parser.add_argument("--real-battery-json", default=str(DEFAULT_REAL_BATTERY_JSON))
    parser.add_argument("--skip-mvp-eval", action="store_true")
    parser.add_argument("--skip-golden-benchmark", action="store_true")
    parser.add_argument("--skip-num-predict-sweep", action="store_true")
    parser.add_argument("--skip-real-battery", action="store_true")
    parser.add_argument("--mvp-limit", type=int, default=None)
    parser.add_argument("--golden-limit", type=int, default=None)
    parser.add_argument("--num-predict-values", default="64,96,110,220")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()

    settings = Settings()
    configure_logging(settings.log_level)

    mvp_dataset = Path(args.mvp_dataset)
    golden_dataset = Path(args.golden_dataset)
    real_battery_json = Path(args.real_battery_json)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    values = [int(item.strip()) for item in args.num_predict_values.split(",") if item.strip()]

    report: dict[str, Any] = {
        "settings": {
            "llm_model": settings.llm_model,
            "llm_num_predict": settings.llm_num_predict,
            "llm_base_url": settings.llm_base_url,
            "catalog_db_enabled": settings.catalog_db_enabled,
            "erp_db_enabled": settings.erp_db_enabled,
        },
        "mvp_dataset": str(mvp_dataset).replace("\\", "/"),
        "golden_dataset": str(golden_dataset).replace("\\", "/"),
        "mvp_eval": None,
        "golden_benchmark": None,
        "num_predict_sweep": None,
    }

    if not args.skip_mvp_eval:
        report["mvp_eval"] = run_mvp_eval(
            settings=settings,
            dataset_path=mvp_dataset,
            limit=args.mvp_limit,
        )

    if not args.skip_golden_benchmark:
        golden_benchmark = run_golden_benchmark(
            settings=settings,
            dataset_path=golden_dataset,
            num_predict=None,
            limit=args.golden_limit,
        )
        golden_benchmark["dataset"] = str(golden_dataset).replace("\\", "/")
        if args.golden_limit is not None and args.golden_limit > 0:
            golden_benchmark["dataset_limit"] = args.golden_limit
        report["golden_benchmark"] = golden_benchmark

    if not args.skip_num_predict_sweep:
        report["num_predict_sweep"] = run_num_predict_sweep(
            settings=settings,
            dataset_path=golden_dataset,
            values=values,
            limit=args.golden_limit,
        )

    if not args.skip_real_battery and real_battery_json.exists():
        report["real_battery"] = summarize_real_battery(real_battery_json)
    else:
        report["real_battery"] = None

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "output_json": str(output_json).replace("\\", "/"),
                "output_md": str(output_md).replace("\\", "/"),
                "mvp_dataset": str(mvp_dataset).replace("\\", "/"),
                "golden_dataset": str(golden_dataset).replace("\\", "/"),
                "real_battery_included": report["real_battery"] is not None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
