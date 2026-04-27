from app.config import Settings
from app.infra.postgres_conninfo import (
    build_catalog_conninfo,
    build_erp_conninfo,
    build_postgres_conninfo,
)


def test_build_postgres_conninfo_renders_expected_string() -> None:
    result = build_postgres_conninfo(
        host="db-host",
        port=5433,
        dbname="presearch",
        user="presearch",
        password="secret",
        connect_timeout_s=5,
    )

    assert result == (
        "host=db-host "
        "port=5433 "
        "dbname=presearch "
        "user=presearch "
        "password=secret "
        "connect_timeout=5"
    )


def test_build_catalog_conninfo_uses_catalog_settings() -> None:
    settings = Settings(
        _env_file=None,
        CATALOG_DB_HOST="catalog-host",
        CATALOG_DB_PORT=5434,
        CATALOG_DB_NAME="catalog-db",
        CATALOG_DB_USER="catalog-user",
        CATALOG_DB_PASSWORD="catalog-pass",
        CATALOG_DB_CONNECT_TIMEOUT_S=7,
    )

    assert build_catalog_conninfo(settings) == (
        "host=catalog-host "
        "port=5434 "
        "dbname=catalog-db "
        "user=catalog-user "
        "password=catalog-pass "
        "connect_timeout=7"
    )


def test_build_erp_conninfo_uses_erp_settings() -> None:
    settings = Settings(
        _env_file=None,
        ERP_DB_HOST="erp-host",
        ERP_DB_PORT=5440,
        ERP_DB_NAME="erp-db",
        ERP_DB_USER="erp-user",
        ERP_DB_PASSWORD="erp-pass",
        ERP_DB_CONNECT_TIMEOUT_S=9,
    )

    assert build_erp_conninfo(settings) == (
        "host=erp-host "
        "port=5440 "
        "dbname=erp-db "
        "user=erp-user "
        "password=erp-pass "
        "connect_timeout=9"
    )
