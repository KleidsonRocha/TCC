import pytest

from app.core.domain.review_errors import ReviewValidationError
from app.infra.pre_search_review_admin_pg import PGPreSearchReviewRepository


class _Cursor:
    def __init__(self, *, fetchone=None, fetchall=None, rowcount=1) -> None:
        self.fetchone_values = list(fetchone or [])
        self.fetchall_values = list(fetchall or [])
        self.executed = []
        self.rowcount = rowcount

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_values.pop(0) if self.fetchone_values else None

    def fetchall(self):
        return self.fetchall_values.pop(0) if self.fetchall_values else []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.commits = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_pg_review_marks_only_pending_turn_and_calculates_completion(monkeypatch) -> None:
    cursor = _Cursor(fetchone=[
        {"id": 709, "conversation_id": "webchat:conv", "review_status": "pending"},
        {"interaction_count": 2, "pending_count": 0, "reviewed_count": 2, "promoted_count": 0, "discarded_count": 0},
    ])
    connection = _Connection(cursor)
    monkeypatch.setattr("app.infra.pre_search_review_admin_pg.psycopg.connect", lambda *args, **kwargs: connection)
    repository = object.__new__(PGPreSearchReviewRepository)
    repository._conninfo = "postgresql://test"

    result = repository.review_interaction(
        interaction_id=709,
        decision="search",
        criteria={"part_query": "amortecedores suspensao", "position": "front"},
        items=None,
        missing_fields=[],
        question_key=None,
        question_prompt=None,
        question_options=None,
        reviewed_notes="correto",
        reviewed_by="Kleidson",
    )

    assert connection.commits == 1
    assert result["conversation_completed"] is True
    assert "review_status = 'reviewed'" in cursor.executed[1][0]
    assert cursor.executed[1][1][-1] == 709


def test_pg_review_list_filters_pending_conversations(monkeypatch) -> None:
    cursor = _Cursor(fetchall=[[{"conversation_id": "conv-1", "pending_count": 2}]])
    connection = _Connection(cursor)
    monkeypatch.setattr("app.infra.pre_search_review_admin_pg.psycopg.connect", lambda *args, **kwargs: connection)
    repository = object.__new__(PGPreSearchReviewRepository)
    repository._conninfo = "postgresql://test"

    rows = repository.list_conversations(status="pending", limit=25)

    assert rows == [{"conversation_id": "conv-1", "pending_count": 2}]
    sql, params = cursor.executed[0]
    assert "review_status = 'pending'" in sql
    assert params == (25,)


def test_pg_review_rejects_part_code_not_written_by_user(monkeypatch) -> None:
    cursor = _Cursor(fetchone=[{
        "id": 710,
        "conversation_id": "webchat:conv",
        "review_status": "pending",
        "message_text": "pastilha para gol 2010",
        "last_messages": [],
    }])
    connection = _Connection(cursor)
    monkeypatch.setattr("app.infra.pre_search_review_admin_pg.psycopg.connect", lambda *args, **kwargs: connection)
    repository = object.__new__(PGPreSearchReviewRepository)
    repository._conninfo = "postgresql://test"

    with pytest.raises(ReviewValidationError, match="literalmente"):
        repository.review_interaction(
            interaction_id=710,
            decision="search",
            criteria={"part_query": "pastilhas de freio", "part_code": "FREIO-2010"},
            items=None,
            missing_fields=[],
            question_key=None,
            question_prompt=None,
            question_options=None,
            reviewed_notes=None,
            reviewed_by="Kleidson",
        )

    assert connection.commits == 0


def test_pg_review_reopens_turn_and_preserves_snapshot(monkeypatch) -> None:
    cursor = _Cursor(fetchone=[
        {
            "id": 677,
            "conversation_id": "eval-real-019",
            "review_status": "reviewed",
            "reviewed_decision": "ask",
            "reviewed_criteria": {"vehicle_model": "HILUX"},
            "reviewed_items": None,
        },
        {"interaction_count": 2, "pending_count": 2, "reviewed_count": 0, "promoted_count": 0, "discarded_count": 0},
    ])
    connection = _Connection(cursor)
    monkeypatch.setattr("app.infra.pre_search_review_admin_pg.psycopg.connect", lambda *args, **kwargs: connection)
    repository = object.__new__(PGPreSearchReviewRepository)
    repository._conninfo = "postgresql://test"

    result = repository.reopen_interaction(
        interaction_id=677, reviewed_notes="corrigir marca", reviewed_by="Kleidson"
    )

    assert result["review_status"] == "pending"
    assert connection.commits == 1
    assert "pre_search_review_revision" in cursor.executed[1][0]
    assert "reviewed_items = NULL" in cursor.executed[2][0]
