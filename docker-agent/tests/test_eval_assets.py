import json
import sys
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings
from app.infra.pre_search_benchmark import load_dataset
from scripts.eval import benchmark_llm_num_predict, evaluate_pre_search


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


def test_evaluate_pre_search_main_uses_mvp_dataset_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: dict[str, Any] = {}

    def fake_load_dataset(path: Path) -> list[dict[str, Any]]:
        calls["path"] = path
        return []

    monkeypatch.setattr(evaluate_pre_search, "_load_dataset", fake_load_dataset)
    monkeypatch.setattr(evaluate_pre_search, "_pick_validator", lambda settings: object())
    monkeypatch.setattr(evaluate_pre_search, "configure_logging", lambda level: None)

    evaluate_pre_search.main()

    assert calls["path"] == MVP_DATASET_PATH
    payload = json.loads(capsys.readouterr().out)
    assert payload["dataset_size"] == 0


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
