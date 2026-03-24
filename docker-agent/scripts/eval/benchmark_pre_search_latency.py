import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.infra.logger import configure_logging, get_logger
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


@dataclass(frozen=True)
class Scenario:
    name: str
    message_text: str
    context_last_messages: list[dict[str, str]]
    notes: str


DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="ask_minimal",
        message_text="preciso de uma peca",
        context_last_messages=[],
        notes="Caso curto que tende a virar ask por falta de part_query.",
    ),
    Scenario(
        name="search_complete",
        message_text="filtro oleo gol 2015",
        context_last_messages=[],
        notes="Caso objetivo com part_query, modelo e ano.",
    ),
    Scenario(
        name="follow_up_engine",
        message_text="1.0",
        context_last_messages=[
            {"role": "user", "text": "correia dentada gol 2010"},
            {"role": "assistant", "text": "Qual a motorizacao do veiculo?"},
        ],
        notes="Caso de follow-up com historico curto.",
    ),
    Scenario(
        name="handoff_request",
        message_text="quero falar com atendimento humano",
        context_last_messages=[],
        notes="Caso exploratorio para observar se a LLM escolhe handoff.",
    ),
)


def _normalize_model_name(value: str | None) -> str:
    return str(value or "").strip().lower()


def _safe_percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 2)
    ordered = sorted(values)
    rank = max(0.0, min(percentile, 1.0)) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    interpolated = ordered[lower] * (1 - weight) + ordered[upper] * weight
    return round(interpolated, 2)


def _fetch_ollama_ps(*, base_url: str, timeout_s: float, target_model: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "ok": False,
        "target_loaded": False,
        "loaded_model_names": [],
        "models": [],
        "error": None,
    }
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/api/ps",
            timeout=max(5.0, min(timeout_s, 30.0)),
        )
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", []) if isinstance(payload, dict) else []
        simplified_models: list[dict[str, Any]] = []
        loaded_names: list[str] = []
        target = _normalize_model_name(target_model)
        for raw_model in models:
            if not isinstance(raw_model, dict):
                continue
            name = str(raw_model.get("name") or raw_model.get("model") or "").strip()
            normalized_name = _normalize_model_name(name)
            if not name:
                continue
            loaded_names.append(name)
            simplified_models.append(
                {
                    "name": name,
                    "size_vram": raw_model.get("size_vram"),
                    "expires_at": raw_model.get("expires_at"),
                }
            )
        snapshot["ok"] = True
        snapshot["loaded_model_names"] = loaded_names
        snapshot["models"] = simplified_models
        snapshot["target_loaded"] = any(_normalize_model_name(name) == target for name in loaded_names)
    except Exception as exc:  # pragma: no cover - depends on external service
        snapshot["error"] = str(exc)
    return snapshot


def _measure_single_call(
    *,
    validator: LLMPreSearchValidator,
    scenario: Scenario,
    phase: str,
) -> dict[str, Any]:
    ps_before = _fetch_ollama_ps(
        base_url=validator._base_url,  # type: ignore[attr-defined]
        timeout_s=validator._timeout,  # type: ignore[attr-defined]
        target_model=validator._model,  # type: ignore[attr-defined]
    )

    extractor_started_at = time.perf_counter()
    extracted = validator._dictionary_extractor.extract(  # type: ignore[attr-defined]
        scenario.message_text,
        last_messages=scenario.context_last_messages,
    )
    extractor_ms = round((time.perf_counter() - extractor_started_at) * 1000, 2)

    started_at = time.perf_counter()
    validation = validator.validate(
        scenario.message_text,
        last_messages=scenario.context_last_messages,
    )
    total_ms = round((time.perf_counter() - started_at) * 1000, 2)

    ps_after = _fetch_ollama_ps(
        base_url=validator._base_url,  # type: ignore[attr-defined]
        timeout_s=validator._timeout,  # type: ignore[attr-defined]
        target_model=validator._model,  # type: ignore[attr-defined]
    )
    audit = validator.get_last_audit() or {}

    return {
        "phase": phase,
        "scenario": scenario.name,
        "message_text": scenario.message_text,
        "context_last_messages": scenario.context_last_messages,
        "notes": scenario.notes,
        "dictionary_seed_criteria": extracted.model_dump(exclude_none=True),
        "extractor_ms": extractor_ms,
        "validate_total_ms": total_ms,
        "decision": validation.decision,
        "criteria": validation.criteria.model_dump(exclude_none=True),
        "missing_fields": list(validation.missing_fields),
        "next_question": (
            validation.next_question.model_dump(exclude_none=True)
            if validation.next_question
            else None
        ),
        "confidence": validation.confidence,
        "llm_audit": audit,
        "ollama_ps_before": ps_before,
        "ollama_ps_after": ps_after,
    }


def _summarize_measurements(measurements: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(item["validate_total_ms"]) for item in measurements]
    extractor_latencies = [float(item["extractor_ms"]) for item in measurements]
    decisions = [str(item["decision"]) for item in measurements]
    target_loaded_before = [
        bool(item["ollama_ps_before"].get("target_loaded"))
        for item in measurements
        if isinstance(item.get("ollama_ps_before"), dict)
    ]
    target_loaded_after = [
        bool(item["ollama_ps_after"].get("target_loaded"))
        for item in measurements
        if isinstance(item.get("ollama_ps_after"), dict)
    ]
    return {
        "count": len(measurements),
        "latency_avg_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "latency_min_ms": round(min(latencies), 2) if latencies else 0.0,
        "latency_max_ms": round(max(latencies), 2) if latencies else 0.0,
        "latency_p50_ms": _safe_percentile(latencies, 0.50),
        "latency_p95_ms": _safe_percentile(latencies, 0.95),
        "extractor_avg_ms": round(statistics.mean(extractor_latencies), 2) if extractor_latencies else 0.0,
        "decisions": decisions,
        "target_loaded_before_all": all(target_loaded_before) if target_loaded_before else False,
        "target_loaded_after_all": all(target_loaded_after) if target_loaded_after else False,
    }


def _run_sequence_battery(
    *,
    validator: LLMPreSearchValidator,
    scenarios: list[Scenario],
    trials: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    by_scenario: dict[str, list[dict[str, Any]]] = {scenario.name: [] for scenario in scenarios}

    for scenario in scenarios:
        for index in range(max(trials, 1)):
            measurement = _measure_single_call(
                validator=validator,
                scenario=scenario,
                phase=f"sequence_{index + 1}",
            )
            rows.append(measurement)
            by_scenario[scenario.name].append(measurement)

    return {
        "measurements": rows,
        "summary_by_scenario": {
            name: _summarize_measurements(items)
            for name, items in by_scenario.items()
        },
    }


def _run_idle_battery(
    *,
    validator: LLMPreSearchValidator,
    scenarios: list[Scenario],
    idle_seconds: list[int],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    summary_by_scenario: dict[str, dict[str, Any]] = {}

    for scenario in scenarios:
        scenario_rows: list[dict[str, Any]] = []
        baseline = _measure_single_call(
            validator=validator,
            scenario=scenario,
            phase="idle_baseline",
        )
        rows.append(baseline)
        scenario_rows.append(baseline)

        for idle_s in idle_seconds:
            before_sleep_ps = _fetch_ollama_ps(
                base_url=validator._base_url,  # type: ignore[attr-defined]
                timeout_s=validator._timeout,  # type: ignore[attr-defined]
                target_model=validator._model,  # type: ignore[attr-defined]
            )
            time.sleep(max(idle_s, 0))
            after_sleep_ps = _fetch_ollama_ps(
                base_url=validator._base_url,  # type: ignore[attr-defined]
                timeout_s=validator._timeout,  # type: ignore[attr-defined]
                target_model=validator._model,  # type: ignore[attr-defined]
            )
            measurement = _measure_single_call(
                validator=validator,
                scenario=scenario,
                phase=f"idle_after_{idle_s}s",
            )
            measurement["idle_seconds"] = idle_s
            measurement["ollama_ps_before_sleep"] = before_sleep_ps
            measurement["ollama_ps_after_sleep"] = after_sleep_ps
            rows.append(measurement)
            scenario_rows.append(measurement)

        summary_by_scenario[scenario.name] = _summarize_measurements(scenario_rows)

    return {
        "measurements": rows,
        "summary_by_scenario": summary_by_scenario,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _scenario_map() -> dict[str, Scenario]:
    return {scenario.name: scenario for scenario in DEFAULT_SCENARIOS}


def _build_stdout_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "settings": report.get("settings"),
        "initial_target_loaded": report.get("initial_ollama_ps", {}).get("target_loaded"),
        "sequence_summary": report.get("sequence_battery", {}).get("summary_by_scenario"),
        "idle_summary": report.get("idle_battery", {}).get("summary_by_scenario"),
        "total_runtime_s": report.get("total_runtime_s"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mede latencia do pre_search_validator em sequencia e apos periodos de idle."
    )
    parser.add_argument("--sequence-trials", type=int, default=3)
    parser.add_argument("--idle-seconds", type=int, nargs="*", default=[30, 330])
    parser.add_argument(
        "--idle-scenarios",
        nargs="*",
        default=["ask_minimal", "search_complete"],
        help="Nomes dos cenarios que vao passar pelos waits de idle.",
    )
    parser.add_argument(
        "--output",
        default="docs/assets/reports/pre_search_validator_latency_report.json",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger()

    catalog = resolve_pre_search_catalog(settings=settings, logger=logger)
    validator = LLMPreSearchValidator(
        settings=settings,
        logger=logger,
        catalog=catalog,
    )

    scenario_lookup = _scenario_map()
    sequence_scenarios = list(DEFAULT_SCENARIOS)
    idle_scenarios = [
        scenario_lookup[name]
        for name in args.idle_scenarios
        if name in scenario_lookup
    ]

    started_at = time.perf_counter()
    report = {
        "generated_at_epoch_s": round(time.time(), 3),
        "settings": {
            "llm_base_url": settings.llm_base_url,
            "llm_model": settings.llm_model,
            "llm_num_predict": settings.llm_num_predict,
            "llm_keep_alive": settings.llm_keep_alive,
            "llm_temperature": settings.llm_temperature,
            "llm_timeout_ms": settings.llm_timeout_ms,
        },
        "initial_ollama_ps": _fetch_ollama_ps(
            base_url=settings.llm_base_url,
            timeout_s=max(settings.llm_timeout_ms, 1000) / 1000,
            target_model=settings.llm_model,
        ),
        "sequence_battery": _run_sequence_battery(
            validator=validator,
            scenarios=sequence_scenarios,
            trials=args.sequence_trials,
        ),
        "idle_battery": _run_idle_battery(
            validator=validator,
            scenarios=idle_scenarios,
            idle_seconds=list(args.idle_seconds),
        ),
    }
    report["total_runtime_s"] = round(time.perf_counter() - started_at, 2)

    output_path = Path(args.output)
    _write_json(output_path, report)

    print(json.dumps(_build_stdout_summary(report), ensure_ascii=False, indent=2))
    print(f"\nRelatorio salvo em: {output_path}")


if __name__ == "__main__":
    main()
