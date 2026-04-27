from app.config import Settings


def build_postgres_conninfo(
    *,
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    connect_timeout_s: int,
) -> str:
    return (
        f"host={host} "
        f"port={port} "
        f"dbname={dbname} "
        f"user={user} "
        f"password={password} "
        f"connect_timeout={connect_timeout_s}"
    )


def build_catalog_conninfo(settings: Settings) -> str:
    return build_postgres_conninfo(
        host=settings.catalog_db_host,
        port=settings.catalog_db_port,
        dbname=settings.catalog_db_name,
        user=settings.catalog_db_user,
        password=settings.catalog_db_password,
        connect_timeout_s=settings.catalog_db_connect_timeout_s,
    )


def build_erp_conninfo(settings: Settings) -> str:
    return build_postgres_conninfo(
        host=settings.erp_db_host,
        port=settings.erp_db_port,
        dbname=settings.erp_db_name,
        user=settings.erp_db_user,
        password=settings.erp_db_password,
        connect_timeout_s=settings.erp_db_connect_timeout_s,
    )
