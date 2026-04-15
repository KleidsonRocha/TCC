import json

import pytest

from app.config import Settings
from scripts.training import review_pre_search_queue


class _FakeCursor:
    def __init__(self, *, fetchone_results=None, fetchall_results=None) -> None:
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, sql, params=None) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)

    def fetchall(self):
        if not self._fetchall_results:
            return []
        return self._fetchall_results.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0

    def cursor(self):
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _settings() -> Settings:
    return Settings(
        APP_ENV="test",
        LOG_LEVEL="INFO",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        CATALOG_DB_HOST="presearch-db",
        CATALOG_DB_PORT=5432,
        CATALOG_DB_NAME="presearch",
        CATALOG_DB_USER="presearch",
        CATALOG_DB_PASSWORD="presearch",
    )


def test_json_value_returns_default_for_blank_and_parses_json() -> None:
    assert review_pre_search_queue._json_value("", default=["fallback"]) == ["fallback"]
    assert review_pre_search_queue._json_value(None, default={"ok": False}) == {"ok": False}
    assert review_pre_search_queue._json_value('{"part_query":"radiador"}', default=None) == {
        "part_query": "radiador"
    }


def test_normalize_example_key_sanitizes_text() -> None:
    result = review_pre_search_queue._normalize_example_key("  Review Capture #12 / Gol 2010  ")

    assert result == "review_capture_12_gol_2010"


def test_review_case_requires_question_when_decision_is_ask() -> None:
    with pytest.raises(ValueError, match="question-key"):
        review_pre_search_queue.review_case(
            settings=_settings(),
            interaction_id=12,
            decision="ask",
            reviewed_by="tester",
            reviewed_notes=None,
            criteria_json=None,
            missing_fields_json=None,
            question_key=None,
            question_prompt=None,
            question_options_json=None,
        )


def test_review_case_updates_reviewed_interaction_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = _FakeCursor(
        fetchone_results=[
            {
                "id": 12,
                "review_status": "reviewed",
                "reviewed_decision": "search",
                "reviewed_question_key": None,
                "reviewed_question_prompt": None,
            }
        ]
    )
    connection = _FakeConnection(cursor)

    class _FakePsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            return connection

    monkeypatch.setattr(review_pre_search_queue, "psycopg", _FakePsycopg)
    monkeypatch.setattr(review_pre_search_queue, "dict_row", object())

    review_pre_search_queue.review_case(
        settings=_settings(),
        interaction_id=12,
        decision="search",
        reviewed_by="Kleidson",
        reviewed_notes="criterio correto",
        criteria_json='{"part_query":"radiador","part_code":"AB-1234"}',
        missing_fields_json="[]",
        question_key=None,
        question_prompt=None,
        question_options_json=None,
    )

    assert connection.commit_count == 1
    sql, params = cursor.executed[0]
    assert "UPDATE pre_search_review_interaction" in sql
    assert params[0] == "search"
    assert getattr(params[1], "obj", None) == {"part_query": "radiador", "part_code": "AB-1234"}
    assert getattr(params[2], "obj", None) == []
    assert params[-1] == 12


def test_promote_cases_promotes_reviewed_search_and_marks_source_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = {
        "id": 44,
        "review_status": "reviewed",
        "message_text": "AB-1234 gol 2010",
        "last_messages": [{"role": "user", "text": "radiador"}],
        "reviewed_decision": "search",
        "reviewed_criteria": {"part_code": "AB-1234", "vehicle_model": "Gol", "vehicle_year": 2010},
        "reviewed_missing_fields": [],
        "predicted_decision": "search",
        "predicted_criteria": {},
        "predicted_missing_fields": [],
        "predicted_confidence": 0.97,
        "reviewed_by": "manual_reviewer",
    }
    cursor = _FakeCursor(
        fetchone_results=[{"id": 7}],
        fetchall_results=[[row]],
    )
    connection = _FakeConnection(cursor)

    class _FakePsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            return connection

    class _FixedDatetime:
        @classmethod
        def utcnow(cls):
            from datetime import datetime

            return datetime(2026, 4, 15, 10, 11, 12)

    monkeypatch.setattr(review_pre_search_queue, "psycopg", _FakePsycopg)
    monkeypatch.setattr(review_pre_search_queue, "dict_row", object())
    monkeypatch.setattr(review_pre_search_queue, "datetime", _FixedDatetime)

    review_pre_search_queue.promote_cases(
        settings=_settings(),
        dataset_slug="pre-search-ft-v1",
        data_split="train",
        interaction_id=None,
        limit=10,
        reviewed_by="Kleidson",
    )

    assert connection.commit_count == 1
    assert len(cursor.executed) == 4

    dataset_sql, dataset_params = cursor.executed[0]
    assert "pre_search_fine_tuning_dataset_header" in dataset_sql
    assert dataset_params == ("pre-search-ft-v1",)

    insert_sql, insert_params = cursor.executed[2]
    assert "INSERT INTO pre_search_fine_tuning_dataset_record" in insert_sql
    assert insert_params[0] == 7
    assert insert_params[2] == "train"
    assert insert_params[3] == "AB-1234 gol 2010"
    assert getattr(insert_params[4], "obj", None) == [{"role": "user", "text": "radiador"}]
    assert insert_params[5] == "search"
    assert getattr(insert_params[6], "obj", None) == {
        "part_code": "AB-1234",
        "vehicle_model": "Gol",
        "vehicle_year": 2010,
    }
    assert getattr(insert_params[7], "obj", None) == []
    assert insert_params[10] == "literal"
    assert getattr(insert_params[11], "obj", None) == ["review_capture", "predicted_search"]
    assert "interaction_id=44" in insert_params[12]
    assert insert_params[-1] == "Kleidson"

    update_sql, update_params = cursor.executed[3]
    assert "UPDATE pre_search_review_interaction" in update_sql
    assert update_params[0] == "pre-search-ft-v1"
    assert update_params[2] == 44
    assert update_params[1].startswith("review_capture_44_20260415101112")


def test_promote_cases_requires_question_for_reviewed_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": 45,
        "review_status": "reviewed",
        "message_text": "radiador gol 2010",
        "last_messages": [],
        "reviewed_decision": "ask",
        "reviewed_criteria": {"part_query": "radiador", "vehicle_model": "Gol", "vehicle_year": 2010},
        "reviewed_missing_fields": ["engine"],
        "reviewed_question_key": "engine",
        "reviewed_question_prompt": "",
        "reviewed_question_options": ["1.0", "1.6"],
        "predicted_decision": "ask",
        "predicted_criteria": {},
        "predicted_missing_fields": ["engine"],
        "predicted_confidence": 0.91,
        "reviewed_by": "manual_reviewer",
    }
    cursor = _FakeCursor(
        fetchone_results=[{"id": 7}],
        fetchall_results=[[row]],
    )
    connection = _FakeConnection(cursor)

    class _FakePsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            return connection

    monkeypatch.setattr(review_pre_search_queue, "psycopg", _FakePsycopg)
    monkeypatch.setattr(review_pre_search_queue, "dict_row", object())

    with pytest.raises(RuntimeError, match="ask sem pergunta revisada"):
        review_pre_search_queue.promote_cases(
            settings=_settings(),
            dataset_slug="pre-search-ft-v1",
            data_split="train",
            interaction_id=None,
            limit=10,
            reviewed_by="Kleidson",
        )
