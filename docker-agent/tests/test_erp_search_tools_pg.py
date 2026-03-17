import logging

import pytest

from app.config import Settings
from app.core.domain.errors import SearchPartsServiceUnavailableError
from app.core.domain.pre_search import SearchCriteria
from app.infra.erp_search_tools_pg import PostgresErpSearchTools
from app.infra import erp_search_tools_pg


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed_sql = None
        self.executed_params = None

    def execute(self, sql, params):
        self.executed_sql = sql
        self.executed_params = params

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

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
        ERP_DB_ENABLED=True,
        ERP_DB_HOST="10.15.1.23",
        ERP_DB_PORT=5430,
        ERP_DB_NAME="soccol",
        ERP_DB_USER="flextotal",
        ERP_DB_PASSWORD="flextotal",
    )


def test_postgres_erp_tools_maps_rows_to_part_items(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {"item_code": "022.1505", "title": "COXIM AMORTECEDOR FORD ECOSPORT", "score": 0.88},
        {"item_code": "022.1553", "title": "COXIM AMORTECEDOR FORD ECOSPORT C/ROL.", "score": 0.81},
    ]
    cursor = _FakeCursor(rows)

    class _FakePsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            return _FakeConnection(cursor)

    monkeypatch.setattr(erp_search_tools_pg, "psycopg", _FakePsycopg)
    monkeypatch.setattr(erp_search_tools_pg, "dict_row", object())

    tools = PostgresErpSearchTools(settings=_settings(), logger=logging.getLogger("test"))
    items = tools.search_parts(
        query="coxim ecosport 2008 1.6",
        branch_id=1,
        criteria=SearchCriteria(
            part_query="coxim",
            vehicle_brand="Ford",
            vehicle_model="Ecosport",
            vehicle_year=2008,
            engine="1.6",
        ),
    )

    assert [item.item_id for item in items] == ["022.1505", "022.1553"]
    assert items[0].score == 0.88
    assert "FROM soccol.item_search_candidates" in cursor.executed_sql
    assert cursor.executed_params["vehicle_model_norm"] == "ecosport"
    assert cursor.executed_params["vehicle_year"] == 2008
    assert cursor.executed_params["part_token_0"] == "%coxim%"


def test_postgres_erp_tools_raises_service_unavailable_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingPsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(erp_search_tools_pg, "psycopg", _FailingPsycopg)
    monkeypatch.setattr(erp_search_tools_pg, "dict_row", object())

    tools = PostgresErpSearchTools(settings=_settings(), logger=logging.getLogger("test"))

    with pytest.raises(SearchPartsServiceUnavailableError):
        tools.search_parts(
            query="coxim ecosport 2008",
            branch_id=1,
            criteria=SearchCriteria(part_query="coxim", vehicle_model="Ecosport", vehicle_year=2008),
        )


def test_postgres_erp_tools_sql_uses_exact_code_match_without_part_query() -> None:
    sql, params = PostgresErpSearchTools._build_search_sql(
        criteria=SearchCriteria(part_code="C.178"),
        limit=10,
    )

    assert "lower(cd_item) = %(part_code_norm)s" in sql
    assert params["part_code_norm"] == "c.178"
    assert params["part_query"] is None
