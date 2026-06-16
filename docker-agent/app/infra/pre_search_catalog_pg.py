from collections import defaultdict
import logging
import re

from app.config import Settings
from app.core.domain.pre_search_catalog import PreSearchCatalog

try:
    import psycopg
except Exception:  # pragma: no cover - optional import for local tooling
    psycopg = None  # type: ignore[assignment]

DEFAULT_CRITERIA_WEIGHTS: dict[str, int] = {
    "part_code": 100,
    "part_query": 45,
    "vehicle_model": 35,
    "vehicle_year": 20,
    "vehicle_brand": 15,
    "engine": 20,
    "side": 10,
    "position": 10,
    "axle": 10,
    "variant": 10,
    "quantity": 5,
}
DEFAULT_MIN_SCORE_TO_SEARCH = 70


class PostgresPreSearchCatalogProvider:
    def __init__(self, *, settings: Settings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger

    def load(self) -> PreSearchCatalog:
        if psycopg is None:
            raise RuntimeError("Driver psycopg indisponivel para carregar catalogo pre-search.")

        conninfo = (
            f"host={self._settings.catalog_db_host} "
            f"port={self._settings.catalog_db_port} "
            f"dbname={self._settings.catalog_db_name} "
            f"user={self._settings.catalog_db_user} "
            f"password={self._settings.catalog_db_password} "
            f"connect_timeout={self._settings.catalog_db_connect_timeout_s}"
        )

        with psycopg.connect(conninfo) as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:
                part_patterns = self._load_part_patterns(cur)
                brand_aliases = self._load_brand_aliases(cur)
                model_aliases = self._load_model_aliases(cur)
                invalid_tokens = self._load_invalid_tokens(cur)
                (
                    generic_parts,
                    needs_side,
                    needs_position,
                    needs_axle,
                    needs_engine,
                    needs_variant,
                ) = self._load_part_rules(cur)
                engine_by_model = self._load_engine_options(cur)
                criteria_weights, min_score_to_search = self._load_search_scoring(cur)
                part_code_patterns = self._load_part_code_patterns(cur)
                known_group_terms = self._load_known_group_terms(cur)

        self._assert_not_empty(part_patterns, "pre_search_part_alias/pre_search_part_type")
        self._assert_not_empty(brand_aliases, "pre_search_brand_alias/pre_search_brand")
        self._assert_not_empty(model_aliases, "pre_search_model_alias/pre_search_model")
        self._assert_not_empty(invalid_tokens, "pre_search_invalid_slot_token")
        self._assert_not_empty(engine_by_model, "pre_search_engine_option")

        self._logger.info(
            "pre_search_catalog_db_loaded",
            extra={
                "part_patterns_count": len(part_patterns),
                "brand_aliases_count": len(brand_aliases),
                "model_aliases_count": len(model_aliases),
                "invalid_tokens_count": len(invalid_tokens),
                "generic_parts_count": len(generic_parts),
                "needs_side_count": len(needs_side),
                "needs_position_count": len(needs_position),
                "needs_axle_count": len(needs_axle),
                "needs_engine_count": len(needs_engine),
                "needs_variant_count": len(needs_variant),
                "engine_models_count": len(engine_by_model),
                "criteria_weights_count": len(criteria_weights),
                "min_score_to_search": min_score_to_search,
                "part_code_patterns_count": len(part_code_patterns),
                "known_group_terms_count": len(known_group_terms),
            },
        )
        return PreSearchCatalog(
            part_patterns=part_patterns,
            brand_aliases=brand_aliases,
            model_aliases=model_aliases,
            invalid_slot_tokens=invalid_tokens,
            generic_ambiguous_parts=generic_parts,
            needs_side=needs_side,
            needs_position=needs_position,
            needs_axle=needs_axle,
            needs_engine=needs_engine,
            needs_variant=needs_variant,
            engine_by_model=engine_by_model,
            criteria_weights=criteria_weights,
            min_score_to_search=min_score_to_search,
            part_code_patterns=part_code_patterns,
            known_group_terms=known_group_terms,
        )

    @staticmethod
    def _assert_not_empty(value: object, table_hint: str) -> None:
        if not value:
            raise RuntimeError(f"Catalogo pre-search sem dados obrigatorios: {table_hint}.")

    @staticmethod
    def _load_part_patterns(cur: "psycopg.Cursor") -> list[tuple[str, tuple[str, ...]]]:
        cur.execute(
            """
            SELECT pt.name_normalized, pa.alias_normalized
            FROM pre_search_part_type pt
            JOIN pre_search_part_alias pa ON pa.part_type_id = pt.id
            WHERE pt.is_active = TRUE AND pa.is_active = TRUE
            ORDER BY pt.name_normalized, pa.alias_normalized
            """
        )
        rows = cur.fetchall()
        alias_by_part: dict[str, list[str]] = defaultdict(list)
        for part_name, alias in rows:
            canonical = str(part_name or "").strip().lower()
            alias_text = str(alias or "").strip().lower()
            if not canonical or not alias_text:
                continue
            alias_by_part[canonical].append(alias_text)

        return [
            (canonical, tuple(sorted(set(aliases))))
            for canonical, aliases in sorted(alias_by_part.items())
        ]

    @staticmethod
    def _load_brand_aliases(cur: "psycopg.Cursor") -> dict[str, tuple[str, ...]]:
        cur.execute(
            """
            SELECT b.name, ba.alias_normalized
            FROM pre_search_brand b
            JOIN pre_search_brand_alias ba ON ba.brand_id = b.id
            WHERE b.is_active = TRUE AND ba.is_active = TRUE
            ORDER BY b.name, ba.alias_normalized
            """
        )
        rows = cur.fetchall()
        alias_by_brand: dict[str, list[str]] = defaultdict(list)
        for brand_name, alias in rows:
            brand = str(brand_name or "").strip()
            alias_text = str(alias or "").strip().lower()
            if not brand or not alias_text:
                continue
            alias_by_brand[brand].append(alias_text)

        return {
            brand: tuple(sorted(set(aliases)))
            for brand, aliases in sorted(alias_by_brand.items())
        }

    @classmethod
    def _load_known_group_terms(cls, cur: "psycopg.Cursor") -> set[str]:
        cur.execute(
            """
            SELECT name_normalized
            FROM pre_search_part_group
            WHERE is_active = TRUE
            ORDER BY name_normalized
            """
        )
        terms: set[str] = set()
        for (raw_group_name,) in cur.fetchall():
            group_name = str(raw_group_name or "").strip().lower()
            if not group_name:
                continue
            terms.update(cls._expand_group_terms(group_name))
        terms.difference_update({"e", "de", "do", "da", "para", "uso", "geral"})
        terms.discard("")
        return terms

    @staticmethod
    def _expand_group_terms(group_name: str) -> set[str]:
        terms = {group_name}
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", group_name or "")
            if len(token) >= 3
        ]
        for token in tokens:
            terms.add(token)
            if token.endswith("oes") and len(token) > 4:
                terms.add(f"{token[:-3]}ao")
            elif token.endswith("ais") and len(token) > 4:
                terms.add(f"{token[:-3]}al")
            elif token.endswith("res") and len(token) > 5:
                terms.add(token[:-2])
            elif token.endswith("as") and len(token) > 4:
                terms.add(token[:-1])
            elif token.endswith("es") and len(token) > 4:
                terms.add(token[:-2])
            elif token.endswith("s") and len(token) > 4:
                terms.add(token[:-1])
        return terms

    @staticmethod
    def _load_model_aliases(cur: "psycopg.Cursor") -> dict[str, tuple[str, ...]]:
        cur.execute(
            """
            SELECT m.name, ma.alias_normalized
            FROM pre_search_model m
            JOIN pre_search_model_alias ma ON ma.model_id = m.id
            WHERE m.is_active = TRUE AND ma.is_active = TRUE
            ORDER BY m.name, ma.alias_normalized
            """
        )
        rows = cur.fetchall()
        alias_by_model: dict[str, list[str]] = defaultdict(list)
        for model_name, alias in rows:
            model = str(model_name or "").strip()
            alias_text = str(alias or "").strip().lower()
            if not model or not alias_text:
                continue
            alias_by_model[model].append(alias_text)

        return {
            model: tuple(sorted(set(aliases)))
            for model, aliases in sorted(alias_by_model.items())
        }

    @staticmethod
    def _load_invalid_tokens(cur: "psycopg.Cursor") -> set[str]:
        cur.execute(
            """
            SELECT token_normalized
            FROM pre_search_invalid_slot_token
            WHERE is_active = TRUE
            ORDER BY token_normalized
            """
        )
        rows = cur.fetchall()
        values = {str(token or "").strip().lower() for (token,) in rows}
        values.discard("")
        return values

    @staticmethod
    def _load_part_rules(
        cur: "psycopg.Cursor",
    ) -> tuple[set[str], set[str], set[str], set[str], set[str], set[str]]:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'pre_search_part_rule'
              AND column_name IN ('needs_axle', 'needs_variant')
            """
        )
        optional_columns = {str(column_name or "") for (column_name,) in cur.fetchall()}
        needs_axle_sql = "pr.needs_axle" if "needs_axle" in optional_columns else "FALSE"
        needs_variant_sql = "pr.needs_variant" if "needs_variant" in optional_columns else "FALSE"

        cur.execute(
            f"""
            SELECT
                pt.name_normalized,
                pr.is_generic,
                pr.needs_side,
                pr.needs_position,
                {needs_axle_sql} AS needs_axle,
                pr.needs_engine,
                {needs_variant_sql} AS needs_variant
            FROM pre_search_part_rule pr
            JOIN pre_search_part_type pt ON pt.id = pr.part_type_id
            WHERE pt.is_active = TRUE
            ORDER BY pt.name_normalized
            """
        )
        rows = cur.fetchall()
        generic_parts: set[str] = set()
        needs_side: set[str] = set()
        needs_position: set[str] = set()
        needs_axle: set[str] = set()
        needs_engine: set[str] = set()
        needs_variant: set[str] = set()

        for part_name, is_generic, side, position, axle, engine, variant in rows:
            part = str(part_name or "").strip().lower()
            if not part:
                continue
            if bool(is_generic):
                generic_parts.add(part)
            if bool(side):
                needs_side.add(part)
            if bool(position):
                needs_position.add(part)
            if bool(axle):
                needs_axle.add(part)
            if bool(engine):
                needs_engine.add(part)
            if bool(variant):
                needs_variant.add(part)
        return generic_parts, needs_side, needs_position, needs_axle, needs_engine, needs_variant

    @staticmethod
    def _load_engine_options(cur: "psycopg.Cursor") -> dict[str, list[str]]:
        cur.execute(
            """
            SELECT m.name_normalized, eo.engine_option
            FROM pre_search_engine_option eo
            JOIN pre_search_model m ON m.id = eo.model_id
            WHERE m.is_active = TRUE AND eo.is_active = TRUE
            ORDER BY m.name_normalized, eo.sort_order, eo.engine_option
            """
        )
        rows = cur.fetchall()
        values: dict[str, list[str]] = defaultdict(list)
        for model_key, option in rows:
            key = str(model_key or "").strip().lower()
            engine_option = str(option or "").strip()
            if not key or not engine_option:
                continue
            values[key].append(engine_option)

        return {
            key: list(dict.fromkeys(options))
            for key, options in values.items()
        }

    def _load_part_code_patterns(self, cur: "psycopg.Cursor") -> tuple[str, ...]:
        if not self._table_exists(cur, "pre_search_part_code_pattern"):
            return tuple()

        cur.execute(
            """
            SELECT pattern_regex
            FROM pre_search_part_code_pattern
            WHERE is_active = TRUE
            ORDER BY brand_id NULLS FIRST, id
            """
        )
        patterns: list[str] = []
        for (pattern_regex,) in cur.fetchall():
            pattern = str(pattern_regex or "").strip()
            if pattern:
                patterns.append(pattern)
        return tuple(dict.fromkeys(patterns))

    @staticmethod
    def _table_exists(cur: "psycopg.Cursor", table_name: str) -> bool:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s
            )
            """,
            (table_name,),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    def _load_search_scoring(self, cur: "psycopg.Cursor") -> tuple[dict[str, int], int]:
        criteria_weights = dict(DEFAULT_CRITERIA_WEIGHTS)
        min_score_to_search = DEFAULT_MIN_SCORE_TO_SEARCH

        if self._table_exists(cur, "pre_search_criteria_weight"):
            cur.execute(
                """
                SELECT criterion_key, weight
                FROM pre_search_criteria_weight
                WHERE is_active = TRUE
                """
            )
            for criterion_key, weight in cur.fetchall():
                key = str(criterion_key or "").strip().lower()
                if key not in criteria_weights:
                    continue
                try:
                    parsed_weight = int(weight)
                except (TypeError, ValueError):
                    continue
                criteria_weights[key] = max(parsed_weight, 0)

        if self._table_exists(cur, "pre_search_decision_policy"):
            cur.execute(
                """
                SELECT min_score_to_search
                FROM pre_search_decision_policy
                WHERE id = 1
                """
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                try:
                    min_score_to_search = max(int(row[0]), 0)
                except (TypeError, ValueError):
                    min_score_to_search = DEFAULT_MIN_SCORE_TO_SEARCH

        return criteria_weights, min_score_to_search


def resolve_pre_search_catalog(*, settings: Settings, logger: logging.Logger) -> PreSearchCatalog:
    if not settings.catalog_db_enabled:
        raise RuntimeError(
            "Catalogo pre-search em modo strict exige CATALOG_DB_ENABLED=true."
        )

    provider = PostgresPreSearchCatalogProvider(settings=settings, logger=logger)
    return provider.load()
