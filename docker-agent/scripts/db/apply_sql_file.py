import argparse
from pathlib import Path

import psycopg

from app.config import Settings


def _conninfo(
    *,
    settings: Settings,
    db_host: str | None,
    db_port: int | None,
    db_name: str | None,
    db_user: str | None,
    db_password: str | None,
) -> str:
    return (
        f"host={db_host or settings.catalog_db_host} "
        f"port={db_port or settings.catalog_db_port} "
        f"dbname={db_name or settings.catalog_db_name} "
        f"user={db_user or settings.catalog_db_user} "
        f"password={db_password or settings.catalog_db_password} "
        f"connect_timeout={settings.catalog_db_connect_timeout_s}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica um arquivo SQL idempotente no Postgres do projeto.")
    parser.add_argument("--sql-file", required=True, help="Caminho do arquivo SQL.")
    parser.add_argument("--db-host", default=None, help="Host do Postgres.")
    parser.add_argument("--db-port", type=int, default=None, help="Porta do Postgres.")
    parser.add_argument("--db-name", default=None, help="Nome do banco.")
    parser.add_argument("--db-user", default=None, help="Usuario do banco.")
    parser.add_argument("--db-password", default=None, help="Senha do banco.")
    args = parser.parse_args()

    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        raise FileNotFoundError(f"Arquivo SQL nao encontrado: {sql_path}")

    sql_text = sql_path.read_text(encoding="utf-8")
    settings = Settings()
    conninfo = _conninfo(
        settings=settings,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )

    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
        conn.commit()

    print(f"SQL aplicado com sucesso: {sql_path}")


if __name__ == "__main__":
    main()
