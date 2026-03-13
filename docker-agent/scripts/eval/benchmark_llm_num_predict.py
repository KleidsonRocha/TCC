import argparse
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.infra.pre_search_benchmark import benchmark_model, load_dataset


def _pick_recommendation(results: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        results,
        key=lambda item: (
            -item["case_pass_pct"],
            -item["decision_accuracy_pct"],
            -item["criteria_accuracy_pct"],
            -item["missing_fields_accuracy_pct"],
            -item["next_question_key_accuracy_pct"],
            item["latency_p50_ms"],
            item["latency_avg_ms"],
        ),
    )[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de LLM_NUM_PREDICT para pre-search.")
    parser.add_argument(
        "--dataset",
        default="docs/assets/datasets/pre_search_num_predict_golden_set.json",
        help="Caminho do dataset JSON.",
    )
    parser.add_argument(
        "--values",
        default="64,96,110,220",
        help="Lista de valores de num_predict separados por virgula.",
    )
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    settings = Settings()
    values = [int(item.strip()) for item in args.values.split(",") if item.strip()]

    results = []
    for num_predict in values:
        print(f"[benchmark] num_predict={num_predict} started", flush=True)
        result = benchmark_model(
            dataset=dataset,
            settings=settings,
            num_predict=num_predict,
        )
        results.append(result)
        print(
            f"[benchmark] num_predict={num_predict} "
            f"case_pass_pct={result['case_pass_pct']} "
            f"decision_accuracy_pct={result['decision_accuracy_pct']} "
            f"latency_avg_ms={result['latency_avg_ms']}",
            flush=True,
        )

    recommendation = _pick_recommendation(results)
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "values": values,
                "recommendation": {
                    "num_predict": recommendation["num_predict"],
                    "case_pass_pct": recommendation["case_pass_pct"],
                    "decision_accuracy_pct": recommendation["decision_accuracy_pct"],
                    "criteria_accuracy_pct": recommendation["criteria_accuracy_pct"],
                    "missing_fields_accuracy_pct": recommendation["missing_fields_accuracy_pct"],
                    "next_question_key_accuracy_pct": recommendation["next_question_key_accuracy_pct"],
                    "latency_avg_ms": recommendation["latency_avg_ms"],
                    "latency_p50_ms": recommendation["latency_p50_ms"],
                    "latency_p95_ms": recommendation["latency_p95_ms"],
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
