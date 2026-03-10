from collections import defaultdict
import logging

from app.config import Settings
from app.core.domain.pre_search_catalog import PreSearchCatalog

try:
    import psycopg
except Exception:  # pragma: no cover - optional import for local tooling
    psycopg = None  # type: ignore[assignment]


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
                generic_parts, needs_side, needs_position, needs_engine = self._load_part_rules(cur)
                engine_by_model = self._load_engine_options(cur)

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
                "needs_engine_count": len(needs_engine),
                "engine_models_count": len(engine_by_model),
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
            needs_engine=needs_engine,
            engine_by_model=engine_by_model,
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
    def _load_part_rules(cur: "psycopg.Cursor") -> tuple[set[str], set[str], set[str], set[str]]:
        cur.execute(
            """
            SELECT pt.name_normalized, pr.is_generic, pr.needs_side, pr.needs_position, pr.needs_engine
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
        needs_engine: set[str] = set()

        for part_name, is_generic, side, position, engine in rows:
            part = str(part_name or "").strip().lower()
            if not part:
                continue
            if bool(is_generic):
                generic_parts.add(part)
            if bool(side):
                needs_side.add(part)
            if bool(position):
                needs_position.add(part)
            if bool(engine):
                needs_engine.add(part)
        return generic_parts, needs_side, needs_position, needs_engine

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


def resolve_pre_search_catalog(*, settings: Settings, logger: logging.Logger) -> PreSearchCatalog:
    if not settings.catalog_db_enabled:
        raise RuntimeError(
            "Catalogo pre-search em modo strict exige CATALOG_DB_ENABLED=true."
        )

    provider = PostgresPreSearchCatalogProvider(settings=settings, logger=logger)
    return provider.load()
