from __future__ import annotations

import argparse
import csv
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import psycopg


@dataclass
class ImportStats:
    groups_upserted: int = 0
    subgroups_upserted: int = 0
    part_rules_upserted: int = 0
    brands_upserted: int = 0
    models_upserted: int = 0
    engines_upserted: int = 0
    skipped_rows: int = 0


def _normalize_text(value: str) -> str:
    lowered = (value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", no_accents)


def _clean_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text or text in {"-", "--"}:
        return None
    if re.fullmatch(r"\([^)]*\)", text):
        return None
    return re.sub(r"\s+", " ", text)


def _parse_bool(value: str | None) -> bool:
    normalized = _normalize_text(str(value or ""))
    return normalized in {"true", "t", "1", "s", "sim", "yes", "y"}


def _parse_int(value: str | None) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    digits = re.sub(r"[^\d-]", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _parse_year(value: str | None) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if not match:
        return None
    year = int(match.group(1))
    if 1900 <= year <= 2100:
        return year
    return None


def _read_csv(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        rows: list[dict[str, str]] = []
        for row in reader:
            parsed: dict[str, str] = {}
            for raw_key, raw_value in row.items():
                key = str(raw_key or "").strip().strip('"')
                value = str(raw_value or "").strip()
                parsed[key] = value
            rows.append(parsed)
        return rows


def _upsert_part_groups(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    updated_by: str,
    stats: ImportStats,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for row in rows:
        source_code = _parse_int(row.get("cd_grupo"))
        name = _clean_text(row.get("nm_grupo"))
        if source_code is None or not name:
            stats.skipped_rows += 1
            continue
        is_active = _normalize_text(row.get("fl_ativo", "")) != "n"
        cur.execute(
            """
            INSERT INTO pre_search_part_group (
                source_group_code,
                name,
                name_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_group_code) DO UPDATE
            SET name = EXCLUDED.name,
                name_normalized = EXCLUDED.name_normalized,
                is_active = EXCLUDED.is_active,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            RETURNING id
            """,
            (source_code, name, _normalize_text(name), is_active, updated_by),
        )
        mapping[source_code] = int(cur.fetchone()[0])
        stats.groups_upserted += 1
    return mapping


def _upsert_part_types_and_aliases(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    group_id_by_code: dict[int, int],
    updated_by: str,
    stats: ImportStats,
) -> dict[tuple[int, int], int]:
    mapping_by_pair: dict[tuple[int, int], int] = {}
    for row in rows:
        group_code = _parse_int(row.get("cd_grupo"))
        source_subgroup_code = _parse_int(row.get("cd_subgrupo"))
        name = _clean_text(row.get("nm_subgrupo"))
        if group_code is None or source_subgroup_code is None or not name:
            stats.skipped_rows += 1
            continue

        part_group_id = group_id_by_code.get(group_code)
        if part_group_id is None:
            stats.skipped_rows += 1
            continue

        cur.execute(
            """
            INSERT INTO pre_search_part_type (
                part_group_id,
                source_subgroup_code,
                name,
                name_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, %s, TRUE, %s)
            ON CONFLICT (part_group_id, source_subgroup_code) DO UPDATE
            SET part_group_id = EXCLUDED.part_group_id,
                name = EXCLUDED.name,
                name_normalized = EXCLUDED.name_normalized,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            RETURNING id
            """,
            (part_group_id, source_subgroup_code, name, _normalize_text(name), updated_by),
        )
        part_type_id = int(cur.fetchone()[0])
        mapping_by_pair[(group_code, source_subgroup_code)] = part_type_id
        stats.subgroups_upserted += 1

        cur.execute(
            """
            INSERT INTO pre_search_part_alias (
                part_type_id,
                alias,
                alias_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (part_type_id, alias_normalized) DO UPDATE
            SET alias = EXCLUDED.alias,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (part_type_id, name, _normalize_text(name), updated_by),
        )
    return mapping_by_pair


def _upsert_part_rules(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    part_type_id_by_group_and_subgroup: dict[tuple[int, int], int],
    updated_by: str,
    stats: ImportStats,
) -> None:
    for row in rows:
        source_subgroup_code = _parse_int(row.get("part_type_id") or row.get("cd_subgrupo"))
        source_group_code = _parse_int(row.get("cd_grupo"))
        if source_group_code is None or source_subgroup_code is None:
            raise ValueError(
                "CSV de regras invalido: cada linha precisa de cd_grupo e part_type_id/cd_subgrupo."
            )

        part_type_id = part_type_id_by_group_and_subgroup.get((source_group_code, source_subgroup_code))
        if part_type_id is None:
            raise ValueError(
                f"Regra sem correspondencia em subgrupo: cd_grupo={source_group_code}, part_type_id={source_subgroup_code}."
            )

        cur.execute(
            """
            INSERT INTO pre_search_part_rule (
                part_type_id,
                is_generic,
                needs_side,
                needs_position,
                needs_axle,
                needs_engine,
                needs_variant,
                updated_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (part_type_id) DO UPDATE
            SET is_generic = EXCLUDED.is_generic,
                needs_side = EXCLUDED.needs_side,
                needs_position = EXCLUDED.needs_position,
                needs_axle = EXCLUDED.needs_axle,
                needs_engine = EXCLUDED.needs_engine,
                needs_variant = EXCLUDED.needs_variant,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (
                part_type_id,
                _parse_bool(row.get("is_generic")),
                _parse_bool(row.get("needs_side")),
                _parse_bool(row.get("needs_position")),
                _parse_bool(row.get("needs_axle")),
                _parse_bool(row.get("needs_engine")),
                _parse_bool(row.get("needs_variant")),
                updated_by,
            ),
        )
        stats.part_rules_upserted += 1


def _upsert_brands_and_aliases(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    updated_by: str,
    stats: ImportStats,
) -> None:
    for row in rows:
        brand = _clean_text(row.get("montadora"))
        if not brand:
            stats.skipped_rows += 1
            continue
        brand_norm = _normalize_text(brand)
        cur.execute(
            """
            INSERT INTO pre_search_brand (name, name_normalized, is_active, updated_by)
            VALUES (%s, %s, TRUE, %s)
            ON CONFLICT (name_normalized) DO UPDATE
            SET name = EXCLUDED.name,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            RETURNING id
            """,
            (brand, brand_norm, updated_by),
        )
        brand_id = int(cur.fetchone()[0])
        stats.brands_upserted += 1

        cur.execute(
            """
            INSERT INTO pre_search_brand_alias (
                brand_id,
                alias,
                alias_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (alias_normalized) DO UPDATE
            SET brand_id = EXCLUDED.brand_id,
                alias = EXCLUDED.alias,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (brand_id, brand, brand_norm, updated_by),
        )


def _ensure_brand(
    cur: psycopg.Cursor,
    *,
    brand_name: str,
    updated_by: str,
) -> int:
    brand_norm = _normalize_text(brand_name)
    cur.execute(
        """
        INSERT INTO pre_search_brand (name, name_normalized, is_active, updated_by)
        VALUES (%s, %s, TRUE, %s)
        ON CONFLICT (name_normalized) DO UPDATE
        SET name = EXCLUDED.name,
            is_active = TRUE,
            updated_at = NOW(),
            updated_by = EXCLUDED.updated_by
        RETURNING id
        """,
        (brand_name, brand_norm, updated_by),
    )
    brand_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO pre_search_brand_alias (brand_id, alias, alias_normalized, is_active, updated_by)
        VALUES (%s, %s, %s, TRUE, %s)
        ON CONFLICT (alias_normalized) DO NOTHING
        """,
        (brand_id, brand_name, brand_norm, updated_by),
    )
    return brand_id


def _upsert_models_and_aliases(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    default_brand_id: int,
    updated_by: str,
    stats: ImportStats,
) -> dict[str, int]:
    model_id_by_norm: dict[str, int] = {}
    for row in rows:
        model_name = _clean_text(row.get("veiculo"))
        if not model_name:
            stats.skipped_rows += 1
            continue

        model_norm = _normalize_text(model_name)
        cur.execute(
            """
            INSERT INTO pre_search_model (
                brand_id,
                name,
                name_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (brand_id, name_normalized) DO UPDATE
            SET name = EXCLUDED.name,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            RETURNING id
            """,
            (default_brand_id, model_name, model_norm, updated_by),
        )
        model_id = int(cur.fetchone()[0])
        model_id_by_norm[model_norm] = model_id
        stats.models_upserted += 1

        cur.execute(
            """
            INSERT INTO pre_search_model_alias (
                model_id,
                alias,
                alias_normalized,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (alias_normalized) DO UPDATE
            SET model_id = EXCLUDED.model_id,
                alias = EXCLUDED.alias,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (model_id, model_name, model_norm, updated_by),
        )
    return model_id_by_norm


def _upsert_engine_options(
    cur: psycopg.Cursor,
    rows: list[dict[str, str]],
    *,
    model_id_by_norm: dict[str, int],
    default_brand_id: int,
    updated_by: str,
    stats: ImportStats,
) -> None:
    sort_counter_by_model: defaultdict[int, int] = defaultdict(int)

    for row in rows:
        model_name = _clean_text(row.get("veiculo"))
        if not model_name:
            stats.skipped_rows += 1
            continue

        model_norm = _normalize_text(model_name)
        model_id = model_id_by_norm.get(model_norm)
        if model_id is None:
            cur.execute(
                """
                INSERT INTO pre_search_model (
                    brand_id,
                    name,
                    name_normalized,
                    is_active,
                    updated_by
                )
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (brand_id, name_normalized) DO UPDATE
                SET name = EXCLUDED.name,
                    is_active = TRUE,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                RETURNING id
                """,
                (default_brand_id, model_name, model_norm, updated_by),
            )
            model_id = int(cur.fetchone()[0])
            model_id_by_norm[model_norm] = model_id

            cur.execute(
                """
                INSERT INTO pre_search_model_alias (
                    model_id,
                    alias,
                    alias_normalized,
                    is_active,
                    updated_by
                )
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (alias_normalized) DO UPDATE
                SET model_id = EXCLUDED.model_id,
                    alias = EXCLUDED.alias,
                    is_active = TRUE,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                """,
                (model_id, model_name, model_norm, updated_by),
            )

        engine_name = _clean_text(row.get("nome_motor"))
        engine_config = _clean_text(row.get("configuracao_motor"))
        engine_displacement = _clean_text(row.get("cilindrada"))

        engine_option = engine_name or engine_config or engine_displacement
        if not engine_option:
            stats.skipped_rows += 1
            continue

        year_from = _parse_year(row.get("ano_inicial"))
        year_to = _parse_year(row.get("ano_final"))
        if year_from and year_to and year_to < year_from:
            year_from, year_to = year_to, year_from

        sort_counter_by_model[model_id] += 1
        sort_order = sort_counter_by_model[model_id]

        cur.execute(
            """
            INSERT INTO pre_search_engine_option (
                model_id,
                engine_option,
                engine_configuration,
                engine_displacement,
                sort_order,
                year_from,
                year_to,
                is_active,
                updated_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            ON CONFLICT (model_id, engine_option, sort_order) DO UPDATE
            SET engine_configuration = EXCLUDED.engine_configuration,
                engine_displacement = EXCLUDED.engine_displacement,
                year_from = EXCLUDED.year_from,
                year_to = EXCLUDED.year_to,
                is_active = TRUE,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (
                model_id,
                engine_option,
                engine_config,
                engine_displacement,
                sort_order,
                year_from,
                year_to,
                updated_by,
            ),
        )
        stats.engines_upserted += 1


def _truncate_catalog_domain(cur: psycopg.Cursor) -> None:
    cur.execute("DELETE FROM pre_search_engine_option")
    cur.execute("DELETE FROM pre_search_model_alias")
    cur.execute("DELETE FROM pre_search_model")
    cur.execute("DELETE FROM pre_search_brand_alias")
    cur.execute("DELETE FROM pre_search_brand")
    cur.execute("DELETE FROM pre_search_part_rule")
    cur.execute("DELETE FROM pre_search_part_alias")
    cur.execute("DELETE FROM pre_search_part_type")
    cur.execute("DELETE FROM pre_search_part_group")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa catalogo pre-search a partir de CSVs de dominio + aliases."
    )
    parser.add_argument("--grupo-csv", required=True, type=Path)
    parser.add_argument("--subgrupo-csv", required=True, type=Path)
    parser.add_argument("--part-rule-csv", required=True, type=Path)
    parser.add_argument("--vehicle-brand-csv", required=True, type=Path)
    parser.add_argument("--vehicle-model-csv", required=True, type=Path)
    parser.add_argument("--engine-option-csv", required=True, type=Path)
    parser.add_argument("--updated-by", default="csv_import")
    parser.add_argument("--default-model-brand", default="SEM_MARCA_MAPEADA")
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--db-host", default=os.getenv("CATALOG_DB_HOST", "localhost"))
    parser.add_argument("--db-port", default=int(os.getenv("CATALOG_DB_PORT", "5433")), type=int)
    parser.add_argument("--db-name", default=os.getenv("CATALOG_DB_NAME", "presearch"))
    parser.add_argument("--db-user", default=os.getenv("CATALOG_DB_USER", "presearch"))
    parser.add_argument("--db-password", default=os.getenv("CATALOG_DB_PASSWORD", "presearch"))
    args = parser.parse_args()

    csv_paths = [
        args.grupo_csv,
        args.subgrupo_csv,
        args.part_rule_csv,
        args.vehicle_brand_csv,
        args.vehicle_model_csv,
        args.engine_option_csv,
    ]
    missing = [str(path) for path in csv_paths if not path.exists()]
    if missing:
        raise SystemExit(f"Arquivos CSV ausentes: {', '.join(missing)}")

    grupo_rows = _read_csv(args.grupo_csv, delimiter=",")
    subgrupo_rows = _read_csv(args.subgrupo_csv, delimiter=",")
    rule_rows = _read_csv(args.part_rule_csv, delimiter=";")
    brand_rows = _read_csv(args.vehicle_brand_csv, delimiter=",")
    model_rows = _read_csv(args.vehicle_model_csv, delimiter=",")
    engine_rows = _read_csv(args.engine_option_csv, delimiter=",")

    stats = ImportStats()
    conninfo = (
        f"host={args.db_host} "
        f"port={args.db_port} "
        f"dbname={args.db_name} "
        f"user={args.db_user} "
        f"password={args.db_password}"
    )

    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cur:
            if args.replace_existing:
                _truncate_catalog_domain(cur)

            group_id_by_code = _upsert_part_groups(
                cur,
                grupo_rows,
                updated_by=args.updated_by,
                stats=stats,
            )
            part_type_id_by_group_and_subgroup = _upsert_part_types_and_aliases(
                cur,
                subgrupo_rows,
                group_id_by_code=group_id_by_code,
                updated_by=args.updated_by,
                stats=stats,
            )
            _upsert_part_rules(
                cur,
                rule_rows,
                part_type_id_by_group_and_subgroup=part_type_id_by_group_and_subgroup,
                updated_by=args.updated_by,
                stats=stats,
            )

            _upsert_brands_and_aliases(
                cur,
                brand_rows,
                updated_by=args.updated_by,
                stats=stats,
            )

            default_brand_id = _ensure_brand(
                cur,
                brand_name=args.default_model_brand,
                updated_by=args.updated_by,
            )
            model_id_by_norm = _upsert_models_and_aliases(
                cur,
                model_rows,
                default_brand_id=default_brand_id,
                updated_by=args.updated_by,
                stats=stats,
            )
            _upsert_engine_options(
                cur,
                engine_rows,
                model_id_by_norm=model_id_by_norm,
                default_brand_id=default_brand_id,
                updated_by=args.updated_by,
                stats=stats,
            )

        conn.commit()

    print("Importacao concluida.")
    print(f"part_group upsert: {stats.groups_upserted}")
    print(f"part_type upsert: {stats.subgroups_upserted}")
    print(f"part_rule upsert: {stats.part_rules_upserted}")
    print(f"brand upsert: {stats.brands_upserted}")
    print(f"model upsert: {stats.models_upserted}")
    print(f"engine_option upsert: {stats.engines_upserted}")
    print(f"rows skipped: {stats.skipped_rows}")


if __name__ == "__main__":
    main()
