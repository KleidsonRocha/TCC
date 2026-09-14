import json
import sys
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings
from app.infra import pre_search_benchmark
from app.infra.pre_search_benchmark import load_dataset
from scripts.eval import (
    benchmark_llm_num_predict,
    benchmark_pre_search_latency,
    evaluate_pre_search,
)


DATASET_DIR = Path("docs/assets/datasets")
MVP_DATASET_PATH = DATASET_DIR / "pre_search_eval_dataset_mvp.json"
GOLDEN_SET_PATH = DATASET_DIR / "pre_search_num_predict_golden_set.json"


def test_mvp_eval_dataset_has_required_shape() -> None:
    rows = json.loads(MVP_DATASET_PATH.read_text(encoding="utf-8"))

    assert isinstance(rows, list)
    assert rows

    for row in rows:
        assert isinstance(row.get("message.text"), str)
        assert isinstance(row.get("context.last_messages"), list)

        expected = row.get("expected")
        assert isinstance(expected, dict)
        assert expected.get("decision") in {"ask", "search", "handoff"}
        assert isinstance(expected.get("criteria", {}), dict)
        assert isinstance(expected.get("missing_fields"), list)

        next_question = expected.get("next_question")
        if next_question is not None:
            assert isinstance(next_question.get("key"), str)
            assert isinstance(next_question.get("prompt"), str)


def test_golden_set_has_unique_ids_and_required_shape() -> None:
    rows = load_dataset(GOLDEN_SET_PATH)

    assert isinstance(rows, list)
    assert rows

    ids = [str(row.get("id", "")).strip() for row in rows]
    assert all(ids)
    assert len(ids) == len(set(ids))

    for row in rows:
        assert isinstance(row.get("message.text"), str)
        assert isinstance(row.get("context.last_messages"), list)

        expected = row.get("expected")
        assert isinstance(expected, dict)
        assert expected.get("decision") in {"ask", "search", "handoff"}
        assert isinstance(expected.get("criteria", {}), dict)
        assert isinstance(expected.get("missing_fields_contains"), list)
        assert "next_question_key" in expected


def test_golden_set_bandejas_uses_side_not_axle() -> None:
    rows = load_dataset(GOLDEN_SET_PATH)
    bandejas_rows = [
        row
        for row in rows
        if str(row.get("expected", {}).get("criteria", {}).get("part_query", "")).lower() == "bandejas"
    ]

    assert bandejas_rows
    for row in bandejas_rows:
        expected = row["expected"]
        criteria = expected.get("criteria", {})
        assert "axle" not in criteria
        assert "axle" not in expected.get("missing_fields_contains", [])
        assert expected.get("next_question_key") != "axle"


def test_golden_set_coxins_uses_position_not_axle() -> None:
    rows = load_dataset(GOLDEN_SET_PATH)
    coxins_rows = [
        row for row in rows if str(row.get("id", "")).startswith("ask_coxins_")
    ]

    assert len(coxins_rows) == 1
    expected = coxins_rows[0]["expected"]
    assert expected["missing_fields_contains"] == ["position"]
    assert expected["next_question_key"] == "position"
    assert "axle" not in expected["criteria"]


def test_golden_set_pastilhas_corsa_search_does_not_require_engine() -> None:
    rows = load_dataset(GOLDEN_SET_PATH)
    matching_rows = [
        row
        for row in rows
        if row.get("id") == "search_pastilhas_corsa_2011_position"
    ]

    assert len(matching_rows) == 1
    expected = matching_rows[0]["expected"]
    assert expected["decision"] == "search"
    assert expected["criteria"]["position"] == "front"
    assert "engine" not in expected["criteria"]
    assert "engine" not in expected["missing_fields_contains"]


def test_evaluate_pre_search_main_uses_mvp_dataset_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: dict[str, Any] = {}

    def fake_load_dataset(path: Path) -> list[dict[str, Any]]:
        calls["path"] = path
        return []

    monkeypatch.setattr(evaluate_pre_search, "load_dataset", fake_load_dataset)
    monkeypatch.setattr(evaluate_pre_search, "_pick_validator", lambda settings: object())
    monkeypatch.setattr(evaluate_pre_search, "configure_logging", lambda level: None)

    evaluate_pre_search.main()

    assert calls["path"] == MVP_DATASET_PATH
    payload = json.loads(capsys.readouterr().out)
    assert payload["dataset_size"] == 0


def test_make_validator_passes_catalog_to_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    class _FakeValidator:
        def __init__(self, *, settings: Settings, logger: Any, catalog: Any) -> None:
            calls["settings"] = settings
            calls["logger"] = logger
            calls["catalog"] = catalog

    monkeypatch.setattr(pre_search_benchmark, "resolve_pre_search_catalog", lambda **kwargs: {"catalog": True})
    monkeypatch.setattr(pre_search_benchmark, "LLMPreSearchValidator", _FakeValidator)

    settings = Settings(_env_file=None)
    validator = pre_search_benchmark.make_validator(settings=settings)

    assert isinstance(validator, _FakeValidator)
    assert calls["settings"] is settings
    assert calls["catalog"] == {"catalog": True}


def test_benchmark_script_uses_golden_set_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: dict[str, Any] = {}

    def fake_load_dataset(path: Path) -> list[dict[str, Any]]:
        calls["path"] = path
        return [{"id": "case-1"}]

    def fake_benchmark_model(*, dataset: list[dict[str, Any]], settings: Settings, num_predict: int) -> dict[str, Any]:
        assert dataset == [{"id": "case-1"}]
        return {
            "model_name": "qwen2.5:7b",
            "num_predict": num_predict,
            "cases_total": 1,
            "case_pass_pct": 100.0,
            "decision_accuracy_pct": 100.0,
            "criteria_accuracy_pct": 100.0,
            "missing_fields_accuracy_pct": 100.0,
            "next_question_key_accuracy_pct": 100.0,
            "latency_avg_ms": 10.0,
            "latency_p50_ms": 10.0,
            "latency_p95_ms": 10.0,
            "cases": [],
        }

    monkeypatch.setattr(benchmark_llm_num_predict, "load_dataset", fake_load_dataset)
    monkeypatch.setattr(benchmark_llm_num_predict, "benchmark_model", fake_benchmark_model)
    monkeypatch.setattr(sys, "argv", ["benchmark_llm_num_predict.py", "--values", "64"])

    benchmark_llm_num_predict.main()

    assert calls["path"] == GOLDEN_SET_PATH
    output = capsys.readouterr().out
    json_start = output.find("{")
    payload = json.loads(output[json_start:])
    assert payload["dataset"] == str(GOLDEN_SET_PATH)
    assert payload["recommendation"]["num_predict"] == 64


def test_settings_default_golden_set_points_to_versioned_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FT_GOLDEN_SET_FILE", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ft_golden_set_file == str(GOLDEN_SET_PATH).replace("\\", "/")


def test_latency_benchmark_compares_llm_and_deterministic_paths() -> None:
    def row(*, latency_ms: float, path: str) -> dict[str, Any]:
        return {
            "validate_total_ms": latency_ms,
            "extractor_ms": 0.5,
            "decision": "search",
            "pre_search_path": path,
            "ollama_ps_before": {"target_loaded": True},
            "ollama_ps_after": {"target_loaded": True},
        }

    comparison = benchmark_pre_search_latency._build_bypass_comparison(
        {
            "llm": {"search_complete": [row(latency_ms=100.0, path="llm")]},
            "bypass": {
                "search_complete": [
                    row(latency_ms=10.0, path="deterministic_bypass")
                ]
            },
        }
    )

    assert comparison["search_complete"] == {
        "llm_avg_ms": 100.0,
        "bypass_avg_ms": 10.0,
        "saved_ms": 90.0,
        "reduction_pct": 90.0,
        "optimized_path": "deterministic_bypass",
    }
