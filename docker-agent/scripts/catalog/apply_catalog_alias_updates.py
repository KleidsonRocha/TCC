"""Apply versioned lexical aliases without replacing catalog or review data.

Default is a rollback preview. Schema comes from the consolidated bootstrap.
"""

import argparse
import csv
from pathlib import Path

import psycopg

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo
from app.infra.pre_search_text import normalize_pre_search_text


def apply_updates(conn, root: Path) -> dict[str, int]:
    sql = (root / "pre_search_init.sql").read_text(encoding="utf-8")
    schema = sql.split("-- BEGIN VARIANT ALIAS SCHEMA", 1)[1].split("-- END VARIANT ALIAS SCHEMA", 1)[0]
    conn.execute(schema)
    counts = {"part_aliases": 0, "variant_aliases": 0}
    with (root / "csv/pre_search_part_alias.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            target = conn.execute(
                """SELECT pt.id FROM pre_search_part_type pt JOIN pre_search_part_group pg
                   ON pg.id=pt.part_group_id WHERE pg.source_group_code=%s
                   AND pt.source_subgroup_code=%s""",
                (int(row["cd_grupo"]), int(row["cd_subgrupo"])),
            ).fetchone()
            if target is None:
                raise ValueError(f"Familia ausente: {row['cd_grupo']}/{row['cd_subgrupo']}")
            conn.execute(
                """INSERT INTO pre_search_part_alias (part_type_id,alias,alias_normalized,updated_by)
                   VALUES (%s,%s,%s,'seed_csv') ON CONFLICT (part_type_id,alias_normalized)
                   DO UPDATE SET alias=EXCLUDED.alias,is_active=TRUE,updated_by='seed_csv',updated_at=NOW()""",
                (target[0], row["alias"], normalize_pre_search_text(row["alias"])),
            )
            counts["part_aliases"] += 1
    with (root / "csv/pre_search_variant_alias.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            model = normalize_pre_search_text(row["model_normalized"])
            if conn.execute("SELECT 1 FROM pre_search_model WHERE name_normalized=%s", (model,)).fetchone() is None:
                raise ValueError(f"Modelo ausente: {model}")
            conn.execute(
                """INSERT INTO pre_search_variant_alias (model_normalized,variant,alias_normalized)
                   VALUES (%s,%s,%s) ON CONFLICT (model_normalized,alias_normalized)
                   DO UPDATE SET variant=EXCLUDED.variant,is_active=TRUE""",
                (model, row["variant"], normalize_pre_search_text(row["alias_normalized"])),
            )
            counts["variant_aliases"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with psycopg.connect(build_catalog_conninfo(Settings()), autocommit=True) as conn:
        with conn.transaction(force_rollback=not args.apply):
            counts = apply_updates(conn, Path("db/init"))
    print({"applied": args.apply, **counts})


if __name__ == "__main__":
    main()
