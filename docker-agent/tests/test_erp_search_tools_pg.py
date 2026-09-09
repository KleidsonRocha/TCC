import logging

import pytest

from app.config import Settings
from app.core.domain.errors import SearchPartsServiceUnavailableError
from app.core.domain.pre_search import SearchCriteria
from app.infra.erp_search_tools_pg import (
    FallbackErpSearchTools,
    PostgresErpSearchTools,
    resolve_search_tools,
)
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
        {
            "item_code": "022.1505",
            "title": "COXIM AMORTECEDOR FORD ECOSPORT DIANTEIRO C/ROL.",
            "score": 0.88,
            "vehicle_application_text": "ECOSPORT 2003 A 2012",
            "vehicle_complement_names": "XLS | XLT",
            "vehicle_model_motor_names": "1.6 | 2.0",
            "vehicle_model_injection_names": None,
            "vehicle_model_transmission_names": "MANUAL",
        },
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
    assert items[0].attributes == {
        "application": ["ECOSPORT 2003 A 2012"],
        "variant": ["XLS", "XLT"],
        "engine": ["1.6", "2.0"],
        "transmission": ["MANUAL"],
        "position": ["Dianteiro"],
        "feature": ["Com rolamento"],
    }
    assert "FROM soccol.item_search_candidates" in cursor.executed_sql
    assert "vehicle_model_motor_names" in cursor.executed_sql
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


def test_fallback_erp_tools_uses_fallback_when_primary_is_unavailable() -> None:
    class _FailingTools:
        def search_parts(self, query, branch_id, criteria=None):
            raise SearchPartsServiceUnavailableError("offline")

    class _FallbackTools:
        def search_parts(self, query, branch_id, criteria=None):
            return ["fallback-result"]

    tools = FallbackErpSearchTools(
        primary=_FailingTools(),
        fallback=_FallbackTools(),
        logger=logging.getLogger("test"),
    )

    items = tools.search_parts(query="coxim ecosport 2008 1.6", branch_id=1)

    assert items == ["fallback-result"]


def test_resolve_search_tools_returns_local_fallback_backend_when_erp_disabled() -> None:
    settings = Settings(
        APP_ENV="test",
        LOG_LEVEL="INFO",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        ERP_DB_ENABLED=False,
        ERP_FALLBACK_DB_ENABLED=True,
    )

    tools = resolve_search_tools(settings=settings, logger=logging.getLogger("test"))

    assert isinstance(tools, PostgresErpSearchTools)


def test_postgres_erp_tools_sql_uses_exact_code_match_without_part_query() -> None:
    sql, params = PostgresErpSearchTools._build_search_sql(
        criteria=SearchCriteria(part_code="C.178"),
        limit=10,
    )

    assert "lower(cd_item) = %(part_code_norm)s" in sql
    assert params["part_code_norm"] == "c.178"
    assert params["part_query"] is None


def test_product_brand_is_a_soft_ranking_preference_not_a_required_filter() -> None:
    sql, params = PostgresErpSearchTools._build_search_sql(
        criteria=SearchCriteria(
            part_query="velas de ignicao automotivas",
            preferred_product_brand="NGK",
            vehicle_model="Gol",
            vehicle_year=2010,
        ),
        limit=10,
    )

    where_clause = sql.split(
        "FROM soccol.item_search_candidates\n                WHERE ", 1
    )[1].split("\n            )", 1)[0]
    assert "preferred_product_brand_like" not in where_clause
    assert "preferred_product_brand_rank" in sql
    assert "has_preferred_product_brand" in sql
    assert params["preferred_product_brand_like"] == "%NGK%"


def test_resolve_search_tools_returns_postgres_backend_when_enabled() -> None:
    settings = Settings(
        APP_ENV="test",
        LOG_LEVEL="INFO",
        AGENT_PORT=8001,
        DEFAULT_LOCALE="pt-BR",
        DEFAULT_TIMEZONE="America/Sao_Paulo",
        ERP_DB_ENABLED=True,
        ERP_FALLBACK_DB_ENABLED=False,
    )
    tools = resolve_search_tools(settings=settings, logger=logging.getLogger("test"))

    assert isinstance(tools, PostgresErpSearchTools)
