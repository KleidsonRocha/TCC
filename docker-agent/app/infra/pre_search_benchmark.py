import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from app.config import Settings
from app.infra.pre_search_catalog_pg import resolve_pre_search_catalog
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


class _NullLogger:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None

    def exception(self, *args: Any, **kwargs: Any) -> None:
        return None


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_context(raw_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": str(item.get("role", "user")),
            "text": str(item.get("text", "")),
        }
        for item in raw_context
    ]


def values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) or isinstance(expected, str):
        return _normalize_string(actual) == _normalize_string(expected)
    return actual == expected


def percent(ok: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((ok / total) * 100, 2)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(math.floor((len(sorted_values) - 1) * pct))
    return round(sorted_values[index], 2)


def evaluate_case(result: Any, expected: dict[str, Any]) -> dict[str, Any]:
    decision_ok = result.decision == expected.get("decision")

    expected_criteria = expected.get("criteria", {})
    criteria_total = 0
    criteria_ok = 0
    criteria_failures: list[str] = []
    for field_name, expected_value in expected_criteria.items():
        criteria_total += 1
        actual_value = getattr(result.criteria, field_name, None)
        if values_match(actual_value, expected_value):
            criteria_ok += 1
        else:
            criteria_failures.append(field_name)

    expected_missing = [str(item) for item in expected.get("missing_fields_contains", [])]
    missing_total = len(expected_missing)
    missing_ok = 0
    missing_failures: list[str] = []
    for field_name in expected_missing:
        if field_name in result.missing_fields:
            missing_ok += 1
        else:
            missing_failures.append(field_name)

    expected_next_key = expected.get("next_question_key")
    actual_next_key = result.next_question.key if result.next_question else None
    next_key_total = 1
    next_key_ok = 1 if values_match(actual_next_key, expected_next_key) else 0

    case_pass = (
        decision_ok
        and criteria_ok == criteria_total
        and missing_ok == missing_total
        and next_key_ok == next_key_total
    )

    return {
        "case_pass": case_pass,
        "decision_ok": decision_ok,
        "criteria_ok": criteria_ok,
        "criteria_total": criteria_total,
        "criteria_failures": criteria_failures,
        "missing_ok": missing_ok,
        "missing_total": missing_total,
        "missing_failures": missing_failures,
        "next_key_ok": next_key_ok,
        "next_key_total": next_key_total,
        "actual_next_key": actual_next_key,
    }


def build_settings(
    *,
    settings: Settings,
    model_name: str | None = None,
    num_predict: int | None = None,
) -> Settings:
    return Settings(
        APP_ENV=settings.app_env,
        LOG_LEVEL="WARNING",
        AGENT_PORT=settings.agent_port,
        DEFAULT_LOCALE=settings.default_locale,
        DEFAULT_TIMEZONE=settings.default_timezone,
        CATALOG_DB_ENABLED=settings.catalog_db_enabled,
        CATALOG_DB_HOST=settings.catalog_db_host,
        CATALOG_DB_PORT=settings.catalog_db_port,
        CATALOG_DB_NAME=settings.catalog_db_name,
        CATALOG_DB_USER=settings.catalog_db_user,
        CATALOG_DB_PASSWORD=settings.catalog_db_password,
        CATALOG_DB_CONNECT_TIMEOUT_S=settings.catalog_db_connect_timeout_s,
        PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,
        LLM_BASE_URL=settings.llm_base_url,
        LLM_MODEL=model_name or settings.llm_model,
        LLM_TIMEOUT_MS=settings.llm_timeout_ms,
        LLM_TEMPERATURE=settings.llm_temperature,
        LLM_NUM_PREDICT=num_predict if num_predict is not None else settings.llm_num_predict,
        LLM_THINK=settings.llm_think,
        LLM_LOG_RAW_RESPONSE=False,
        LLM_CATEGORIES_FILE=settings.llm_categories_file,
        FT_DATASET_SLUG=settings.ft_dataset_slug,
        FT_TARGET_MODEL_PREFIX=settings.ft_target_model_prefix,
        FT_GOLDEN_SET_FILE=settings.ft_golden_set_file,
        FT_TRAIN_COMMAND=settings.ft_train_command,
        FT_PUBLISH_COMMAND=settings.ft_publish_command,
        FT_ACTIVE_ENV_FILE=settings.ft_active_env_file,
        FT_OLLAMA_BASE_MODEL=settings.ft_ollama_base_model,
        FT_OLLAMA_ARTIFACT_KIND=settings.ft_ollama_artifact_kind,
        FT_OLLAMA_ARTIFACT_PATH=settings.ft_ollama_artifact_path,
        FT_OLLAMA_OUTPUT_DIR=settings.ft_ollama_output_dir,
    )


def make_validator(*, settings: Settings) -> LLMPreSearchValidator:
    logger = _NullLogger()
    catalog = resolve_pre_search_catalog(settings=settings, logger=logger)
    return LLMPreSearchValidator(settings=settings, logger=logger, catalog=catalog)


def benchmark_model(
    *,
    dataset: list[dict[str, Any]],
    settings: Settings,
    model_name: str | None = None,
    num_predict: int | None = None,
) -> dict[str, Any]:
    resolved_settings = build_settings(
        settings=settings,
        model_name=model_name,
        num_predict=num_predict,
    )
    validator = make_validator(settings=resolved_settings)

    case_rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    decision_ok = 0
    criteria_ok = 0
    criteria_total = 0
    missing_ok = 0
    missing_total = 0
    next_key_ok = 0
    next_key_total = 0
    case_pass_total = 0

    for row in dataset:
        message_text = str(row.get("message.text", ""))
        context = as_context(row.get("context.last_messages", []))
        expected = row.get("expected", {})

        started_at = time.perf_counter()
        result = validator.validate(message_text=message_text, last_messages=context)
        latency_ms = (time.perf_counter() - started_at) * 1000
        latencies.append(latency_ms)

        evaluation = evaluate_case(result, expected)
        case_pass_total += 1 if evaluation["case_pass"] else 0
        decision_ok += 1 if evaluation["decision_ok"] else 0
        criteria_ok += evaluation["criteria_ok"]
        criteria_total += evaluation["criteria_total"]
        missing_ok += evaluation["missing_ok"]
        missing_total += evaluation["missing_total"]
        next_key_ok += evaluation["next_key_ok"]
        next_key_total += evaluation["next_key_total"]

        case_rows.append(
            {
                "id": row.get("id"),
                "latency_ms": round(latency_ms, 2),
                "expected_decision": expected.get("decision"),
                "actual_decision": result.decision,
                "expected_next_question_key": expected.get("next_question_key"),
                "actual_next_question_key": evaluation["actual_next_key"],
                "criteria_failures": evaluation["criteria_failures"],
                "missing_failures": evaluation["missing_failures"],
                "case_pass": evaluation["case_pass"],
                "actual_criteria": result.criteria.model_dump(exclude_none=True),
                "actual_missing_fields": result.missing_fields,
            }
        )

    resolved_model_name = model_name or settings.llm_model
    resolved_num_predict = num_predict if num_predict is not None else settings.llm_num_predict
    return {
        "model_name": resolved_model_name,
        "num_predict": resolved_num_predict,
        "cases_total": len(dataset),
        "case_pass_pct": percent(case_pass_total, len(dataset)),
        "decision_accuracy_pct": percent(decision_ok, len(dataset)),
        "criteria_accuracy_pct": percent(criteria_ok, criteria_total),
        "missing_fields_accuracy_pct": percent(missing_ok, missing_total),
        "next_question_key_accuracy_pct": percent(next_key_ok, next_key_total),
        "latency_avg_ms": round(statistics.mean(latencies), 2),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "cases": case_rows,
    }


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()
