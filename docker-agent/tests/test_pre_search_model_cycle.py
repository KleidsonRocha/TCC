from datetime import datetime, timezone
from pathlib import Path

from app.infra.pre_search_model_cycle import (
    candidate_is_better,
    generate_target_model_name,
    update_env_llm_model,
)


def test_generate_target_model_name_uses_prefix_and_timestamp() -> None:
    result = generate_target_model_name(
        prefix="pre-search-qwen2.5-ft",
        now=datetime(2026, 3, 13, 12, 34, 56, tzinfo=timezone.utc),
    )
    assert result == "pre-search-qwen2.5-ft-20260313123456"


def test_candidate_is_better_prefers_quality_before_latency() -> None:
    baseline = {
        "case_pass_pct": 80.0,
        "decision_accuracy_pct": 80.0,
        "criteria_accuracy_pct": 100.0,
        "missing_fields_accuracy_pct": 100.0,
        "next_question_key_accuracy_pct": 80.0,
        "latency_p50_ms": 20000.0,
        "latency_avg_ms": 22000.0,
    }
    candidate = {
        "case_pass_pct": 90.0,
        "decision_accuracy_pct": 90.0,
        "criteria_accuracy_pct": 100.0,
        "missing_fields_accuracy_pct": 100.0,
        "next_question_key_accuracy_pct": 90.0,
        "latency_p50_ms": 25000.0,
        "latency_avg_ms": 26000.0,
    }
    assert candidate_is_better(baseline=baseline, candidate=candidate) is True


def test_update_env_llm_model_rewrites_existing_key(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("APP_ENV=dev\nLLM_MODEL=qwen2.5:7b\nLLM_NUM_PREDICT=220\n", encoding="utf-8")

    update_env_llm_model(env_path=env_path, new_model_name="pre-search-qwen2.5-ft-v2")

    assert env_path.read_text(encoding="utf-8") == (
        "APP_ENV=dev\nLLM_MODEL=pre-search-qwen2.5-ft-v2\nLLM_NUM_PREDICT=220\n"
    )
