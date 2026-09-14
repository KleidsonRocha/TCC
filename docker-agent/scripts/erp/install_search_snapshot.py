"""Validate or install the v2 snapshot in the LOCAL catalog database.

Default: validate the full bootstrap and roll back. --apply keeps the validated
tables and moves previous fallback tables into a separate backup schema.
"""

import argparse
import json
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo


BOOTSTRAP = Path("db/init/pre_search_init.sql")


def snapshot_bootstrap() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8").split(
        "-- BEGIN ERP FALLBACK V2\n", 1
    )[1].split("-- END ERP FALLBACK V2", 1)[0]


def install_snapshot(*, apply: bool = False) -> dict:
    suffix = uuid4().hex[:12]
    staging = "search_snapshot_stage_" + suffix
    backup = "search_snapshot_backup_" + suffix
    bootstrap = "\n".join(
        line for line in snapshot_bootstrap().splitlines()
        if not line.startswith("\\") and line.strip() not in {"BEGIN;", "COMMIT;"}
    ).replace("soccol", staging)
    manifest = json.loads(Path("db/init/fallback/v2/manifest.json").read_text(encoding="utf-8"))
    if manifest["contract_version"] != 2:
        raise ValueError("Snapshot contract must be v2")
    result = {"applied": apply, "backup_schema": None, "rows": {}}
    with psycopg.connect(build_catalog_conninfo(Settings()), autocommit=True) as conn:
        with conn.transaction(force_rollback=not apply):
            conn.execute("SET LOCAL statement_timeout = '10min'")
            conn.execute(bootstrap)
            for name in ("candidates", "applications"):
                table = "item_search_" + name
                count = conn.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(
                    sql.Identifier(staging), sql.Identifier(table)
                )).fetchone()[0]
                if count != manifest["files"][name + ".csv.gz"]["rows"]:
                    raise ValueError(f"Row count mismatch: {name}")
                result["rows"][name] = count
            if apply:
                conn.execute("CREATE SCHEMA IF NOT EXISTS soccol")
                conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(backup)))
                for name in ("applications", "candidates"):
                    table = "item_search_" + name
                    conn.execute(sql.SQL("ALTER TABLE IF EXISTS soccol.{} SET SCHEMA {}").format(
                        sql.Identifier(table), sql.Identifier(backup)
                    ))
                for name in ("candidates", "applications"):
                    table = "item_search_" + name
                    conn.execute(sql.SQL("ALTER TABLE {}.{} SET SCHEMA soccol").format(
                        sql.Identifier(staging), sql.Identifier(table)
                    ))
                conn.execute(sql.SQL("DROP SCHEMA {}").format(sql.Identifier(staging)))
                result["backup_schema"] = backup
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Install after validation; preserve previous tables in a backup schema")
    args = parser.parse_args()
    print(json.dumps(install_snapshot(apply=args.apply), indent=2))


if __name__ == "__main__":
    main()
