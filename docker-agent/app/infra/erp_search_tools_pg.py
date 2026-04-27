import logging
import re
from collections.abc import Iterable

from app.config import Settings
from app.core.domain.errors import SearchPartsServiceUnavailableError
from app.core.domain.models import PartItem
from app.core.domain.pre_search import SearchCriteria
from app.core.ports.tools import ToolsPort
from app.infra.postgres_conninfo import build_erp_conninfo

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional import for local tooling
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

_TOKEN_RE = re.compile(r"[A-Za-z0-9./-]+")
_STOPWORDS = {
    "a",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "sem",
    "um",
    "uma",
}
_SIDE_TOKENS = {"left": "esquerd", "right": "direit"}
_POSITION_TOKENS = {"front": "dianteir", "rear": "traseir"}
_AXLE_TOKENS = {"front": "eixo dianteiro", "rear": "eixo traseiro"}


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _search_tokens(value: str | None) -> list[str]:
    if not value:
        return []

    tokens: list[str] = []
    for match in _TOKEN_RE.findall(value.lower()):
        token = match.strip(".-/")
        if not token or token in _STOPWORDS:
            continue
        if len(token) == 1 and not token.isdigit():
            continue
        tokens.append(token)
    return list(dict.fromkeys(tokens))


class PostgresErpSearchTools(ToolsPort):
    def __init__(self, *, settings: Settings, logger: logging.Logger, result_limit: int = 10) -> None:
        self._settings = settings
        self._logger = logger
        self._result_limit = result_limit

    def search_parts(
        self,
        query: str,
        branch_id: int,
        criteria: SearchCriteria | None = None,
    ) -> list[PartItem]:
        if psycopg is None or dict_row is None:
            raise SearchPartsServiceUnavailableError(
                "Busca de pecas indisponivel: driver do banco ERP nao encontrado."
            )

        resolved_criteria = self._resolve_criteria(query=query, criteria=criteria)
        sql, params = self._build_search_sql(criteria=resolved_criteria, limit=self._result_limit)

        try:
            with psycopg.connect(build_erp_conninfo(self._settings), row_factory=dict_row) as conn:  # type: ignore[union-attr]
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
        except Exception as exc:  # pragma: no cover - exercised with monkeypatch in tests
            self._logger.exception(
                "erp_search_query_failed",
                extra={
                    "branch_id": branch_id,
                    "query": query,
                    "criteria": resolved_criteria.model_dump(exclude_none=True),
                },
            )
            raise SearchPartsServiceUnavailableError(
                "Busca de pecas indisponivel: nao foi possivel consultar o ERP."
            ) from exc

        items = [
            PartItem(
                item_id=str(row["item_code"]),
                title=str(row["title"]),
                score=max(0.0, min(float(row["score"]), 1.0)),
            )
            for row in rows
        ]

        self._logger.info(
            "erp_search_query_finished",
            extra={
                "branch_id": branch_id,
                "query": query,
                "criteria": resolved_criteria.model_dump(exclude_none=True),
                "results_count": len(items),
            },
        )
        return items

    @staticmethod
    def _resolve_criteria(query: str, criteria: SearchCriteria | None) -> SearchCriteria:
        if criteria is not None:
            return criteria

        normalized_query = _normalize_optional_text(query)
        return SearchCriteria(part_query=normalized_query)

    @classmethod
    def _build_search_sql(cls, *, criteria: SearchCriteria, limit: int) -> tuple[str, dict[str, object]]:
        part_query = _normalize_optional_text(criteria.part_query)
        part_code = _normalize_optional_text(criteria.part_code)
        vehicle_brand = _normalize_optional_text(criteria.vehicle_brand)
        vehicle_model = _normalize_optional_text(criteria.vehicle_model)
        engine = _normalize_optional_text(criteria.engine)
        variant = _normalize_optional_text(criteria.variant)
        side_fragment = _SIDE_TOKENS.get(criteria.side or "")
        position_fragment = _POSITION_TOKENS.get(criteria.position or "")
        axle_fragment = _AXLE_TOKENS.get(criteria.axle or "")
        part_tokens = _search_tokens(part_query)

        params: dict[str, object] = {
            "has_part_query": bool(part_query),
            "has_part_code": bool(part_code),
            "has_vehicle_brand": bool(vehicle_brand),
            "has_vehicle_model": bool(vehicle_model),
            "has_vehicle_year": criteria.vehicle_year is not None,
            "has_engine": bool(engine),
            "has_variant": bool(variant),
            "has_side": bool(side_fragment),
            "has_position": bool(position_fragment),
            "has_axle": bool(axle_fragment),
            "part_query": part_query,
            "part_query_like": f"%{part_query}%" if part_query else None,
            "part_query_prefix_like": f"{part_query}%" if part_query else None,
            "part_code_norm": part_code.lower() if part_code else None,
            "vehicle_brand_like": f"%{vehicle_brand}%" if vehicle_brand else None,
            "vehicle_brand_norm": vehicle_brand.lower() if vehicle_brand else None,
            "vehicle_model_like": f"%{vehicle_model}%" if vehicle_model else None,
            "vehicle_model_norm": vehicle_model.lower() if vehicle_model else None,
            "vehicle_year": criteria.vehicle_year,
            "engine_like": f"%{engine}%" if engine else None,
            "variant_like": f"%{variant}%" if variant else None,
            "side_like": f"%{side_fragment}%" if side_fragment else None,
            "position_like": f"%{position_fragment}%" if position_fragment else None,
            "axle_like": f"%{axle_fragment}%" if axle_fragment else None,
            "limit": limit,
        }

        token_filters = cls._build_token_filters(
            field_sql="search_text",
            token_prefix="part_token",
            tokens=part_tokens,
            params=params,
        )
        exact_code_sql = (
            "(lower(cd_item) = %(part_code_norm)s "
            "OR lower(coalesce(cd_original, '')) = %(part_code_norm)s "
            "OR lower(coalesce(cd_fabricante, '')) = %(part_code_norm)s)"
        )
        exact_brand_sql = (
            "EXISTS ("
            "SELECT 1 "
            "FROM regexp_split_to_table(coalesce(vehicle_brand_names, ''), E'\\\\s*\\\\|\\\\s*') AS brand_name "
            "WHERE lower(brand_name) = %(vehicle_brand_norm)s"
            ")"
        )
        exact_model_sql = (
            "EXISTS ("
            "SELECT 1 "
            "FROM regexp_split_to_table(coalesce(vehicle_model_names, ''), E'\\\\s*\\\\|\\\\s*') AS model_name "
            "WHERE lower(model_name) = %(vehicle_model_norm)s"
            ")"
        )
        year_match_sql = (
            "%(vehicle_year)s BETWEEN COALESCE(vehicle_year_start, 1900) "
            "AND COALESCE(NULLIF(vehicle_year_end, 0), 2100)"
        )
        brand_filter_sql = "coalesce(vehicle_brand_names, '') ILIKE %(vehicle_brand_like)s"
        model_filter_sql = "coalesce(vehicle_model_names, '') ILIKE %(vehicle_model_like)s"
        engine_match_sql = "coalesce(vehicle_model_motor_names, '') ILIKE %(engine_like)s"
        variant_match_sql = (
            "("
            "coalesce(candidate_title, '') ILIKE %(variant_like)s "
            "OR coalesce(vehicle_application_text, '') ILIKE %(variant_like)s"
            ")"
        )
        side_match_sql = "coalesce(search_text, '') ILIKE %(side_like)s"
        position_match_sql = "coalesce(search_text, '') ILIKE %(position_like)s"
        axle_match_sql = "coalesce(search_text, '') ILIKE %(axle_like)s"

        required_filters: list[str] = []
        if part_code:
            required_filters.append(exact_code_sql)
        if part_tokens:
            required_filters.extend(token_filters)
        if vehicle_brand:
            required_filters.append(brand_filter_sql)
        if vehicle_model:
            required_filters.append(model_filter_sql)
        if criteria.vehicle_year:
            required_filters.append(year_match_sql)
        if engine:
            required_filters.append(engine_match_sql)
        if variant:
            required_filters.append(variant_match_sql)
        if side_fragment:
            required_filters.append(side_match_sql)
        if position_fragment:
            required_filters.append(position_match_sql)
        if axle_fragment:
            required_filters.append(axle_match_sql)

        where_sql = " AND ".join(required_filters) if required_filters else "TRUE"
        part_query_for_penalty = part_query.lower() if part_query else None
        params["part_query_norm"] = part_query_for_penalty

        sql = f"""
            WITH ranked AS (
                SELECT
                    id_item,
                    COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
                    candidate_title AS title,
                    CASE
                        WHEN %(has_part_code)s AND {exact_code_sql} THEN 1.0
                        ELSE
                            0.0
                            + CASE
                                WHEN %(has_part_query)s AND candidate_title ILIKE %(part_query_prefix_like)s THEN 0.32
                                WHEN %(has_part_query)s AND candidate_title ILIKE %(part_query_like)s THEN 0.24
                                WHEN %(has_part_query)s AND search_text ILIKE %(part_query_like)s THEN 0.16
                                ELSE 0.0
                            END
                            + CASE WHEN %(has_vehicle_brand)s AND {exact_brand_sql} THEN 0.08 ELSE 0.0 END
                            + CASE WHEN %(has_vehicle_model)s AND {exact_model_sql} THEN 0.16 ELSE 0.0 END
                            + CASE WHEN %(has_vehicle_year)s AND {year_match_sql} THEN 0.08 ELSE 0.0 END
                            + CASE WHEN %(has_engine)s AND {engine_match_sql} THEN 0.08 ELSE 0.0 END
                            + CASE WHEN %(has_variant)s AND {variant_match_sql} THEN 0.05 ELSE 0.0 END
                            + CASE WHEN %(has_side)s AND {side_match_sql} THEN 0.03 ELSE 0.0 END
                            + CASE WHEN %(has_position)s AND {position_match_sql} THEN 0.04 ELSE 0.0 END
                            + CASE WHEN %(has_axle)s AND {axle_match_sql} THEN 0.03 ELSE 0.0 END
                            - CASE
                                WHEN %(part_query_norm)s = 'amortecedor' AND candidate_title ILIKE 'COXIM %%' THEN 0.10
                                WHEN %(part_query_norm)s = 'amortecedor' AND candidate_title ILIKE 'KIT %%' THEN 0.08
                                ELSE 0.0
                            END
                    END AS score,
                    CASE
                        WHEN %(has_vehicle_model)s AND {exact_model_sql} THEN 0
                        ELSE 1
                    END AS model_rank,
                    CASE
                        WHEN %(has_part_query)s AND candidate_title ILIKE %(part_query_prefix_like)s THEN 0
                        ELSE 1
                    END AS title_rank
                FROM soccol.item_search_candidates
                WHERE {where_sql}
            )
            SELECT
                item_code,
                title,
                ROUND(GREATEST(0.0, LEAST(score, 1.0))::numeric, 4) AS score
            FROM ranked
            WHERE score >= 0.12
            ORDER BY score DESC, model_rank ASC, title_rank ASC, length(title) ASC, item_code ASC
            LIMIT %(limit)s
        """
        return sql, params

    @staticmethod
    def _build_token_filters(
        *,
        field_sql: str,
        token_prefix: str,
        tokens: Iterable[str],
        params: dict[str, object],
    ) -> list[str]:
        filters: list[str] = []
        for index, token in enumerate(tokens):
            key = f"{token_prefix}_{index}"
            params[key] = f"%{token}%"
            filters.append(f"{field_sql} ILIKE %({key})s")
        return filters


def resolve_search_tools(*, settings: Settings, logger: logging.Logger) -> ToolsPort:
    if settings.erp_db_enabled:
        logger.info(
            "search_tools_resolved",
            extra={
                "search_tools_backend": "erp_postgres",
                "erp_db_host": settings.erp_db_host,
                "erp_db_port": settings.erp_db_port,
                "erp_db_name": settings.erp_db_name,
            },
        )
        return PostgresErpSearchTools(settings=settings, logger=logger)

    logger.error(
        "search_tools_unconfigured",
        extra={
            "search_tools_backend": "none",
            "erp_db_enabled": settings.erp_db_enabled,
        },
    )
    raise RuntimeError(
        "Busca real de pecas nao configurada: defina ERP_DB_ENABLED=true para iniciar o docker-agent."
    )
