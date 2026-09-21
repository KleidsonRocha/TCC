import logging
import re

from app.config import Settings
from app.core.domain.errors import SearchPartsServiceUnavailableError
from app.core.domain.models import PartItem
from app.core.domain.result_disambiguation import SEARCH_CANDIDATE_LIMIT
from app.core.domain.pre_search import SearchCriteria
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.core.ports.tools import ToolsPort
from app.infra.postgres_conninfo import build_catalog_conninfo, build_erp_conninfo
from app.infra.erp_search_query import build_search_sql
from app.infra.pre_search_text import normalize_pre_search_text

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional import for local tooling
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

_ATTRIBUTE_SPLIT_RE = re.compile(r"\s*(?:\||;|\r?\n)\s*")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


class FallbackErpSearchTools(ToolsPort):
    def __init__(
        self,
        *,
        primary: ToolsPort,
        fallback: ToolsPort,
        logger: logging.Logger,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._logger = logger

    def search_parts(
        self,
        query: str,
        branch_id: int,
        criteria: SearchCriteria | None = None,
    ) -> list[PartItem]:
        try:
            return self._primary.search_parts(
                query=query,
                branch_id=branch_id,
                criteria=criteria,
            )
        except SearchPartsServiceUnavailableError:
            self._logger.warning(
                "erp_search_primary_failed_using_fallback",
                extra={
                    "branch_id": branch_id,
                    "query": query,
                    "criteria": criteria.model_dump(exclude_none=True) if criteria else None,
                },
                exc_info=True,
            )
            return self._fallback.search_parts(
                query=query,
                branch_id=branch_id,
                criteria=criteria,
            )


class PostgresErpSearchTools(ToolsPort):
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        result_limit: int = SEARCH_CANDIDATE_LIMIT,
        conninfo: str | None = None,
        backend_name: str = "erp_postgres",
        catalog: PreSearchCatalog | None = None,
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._result_limit = result_limit
        self._conninfo = conninfo
        self._backend_name = backend_name
        self._family_ids = catalog.part_family_ids if catalog else None
        self._needs_title_identity = catalog.needs_title_identity if catalog else set()

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
        family_ids = (
            self._family_ids.get(normalize_pre_search_text(resolved_criteria.part_query), [])
            if self._family_ids is not None else None
        )
        canonical_part = normalize_pre_search_text(resolved_criteria.part_query)
        sql, params = self._build_search_sql(
            criteria=resolved_criteria,
            limit=self._result_limit,
            family_ids=family_ids,
            require_family_title_identity=canonical_part in self._needs_title_identity,
        )

        try:
            conninfo = self._conninfo or build_erp_conninfo(self._settings)
            # The ERP database uses WIN1252. Force libpq to transcode text and
            # JSON values before psycopg's JSON loader decodes them in Python.
            # This matches the snapshot exporter and keeps the live and local
            # search paths on the same UTF-8 contract.
            with psycopg.connect(  # type: ignore[union-attr]
                conninfo,
                row_factory=dict_row,
                client_encoding="UTF8",
                options=(
                    f"-c statement_timeout={max(self._settings.erp_search_timeout_ms, 1)}"
                ),
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
        except Exception as exc:  # pragma: no cover - exercised with monkeypatch in tests
            self._logger.exception(
                "erp_search_query_failed",
                extra={
                    "search_tools_backend": self._backend_name,
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
                attributes=self._build_disambiguation_attributes(row),
            )
            for row in rows
        ]

        self._logger.info(
            "erp_search_query_finished",
            extra={
                "search_tools_backend": self._backend_name,
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

    _build_search_sql = staticmethod(build_search_sql)

    @classmethod
    def _build_disambiguation_attributes(cls, row: dict[str, object]) -> dict[str, list[str]]:
        title = str(row.get("title") or "")
        # Only structured, matching application rows may supply vehicle attributes.
        applications = row.get("applications") or []
        application_labels = []
        for application in applications:
            start = application.get("year_start")
            end = application.get("year_end")
            years = (
                f"{start} em diante" if start and application.get("year_open_end")
                else f"{start} a {end}" if start and end
                else "ano nao informado"
            )
            application_labels.append(
                f"{application['vehicle_brand']} {application['vehicle_model']} {years}"
            )
        attributes = {
            "application": cls._split_attribute_values(application_labels),
            **{
                key: cls._split_attribute_values([
                    value for application in applications
                    for value in (application.get(source) or [])
                ])
                for key, source in (
                    ("variant", "variants"), ("engine", "engines"),
                    ("injection", "injections"), ("transmission", "transmissions"),
                )
            },
            "side": cls._infer_directional_attribute(
                title,
                {"esquerd": "Esquerdo", "direit": "Direito"},
            ),
            "position": cls._infer_directional_attribute(
                title,
                {"dianteir": "Dianteiro", "traseir": "Traseiro"},
            ),
            "feature": cls._infer_feature_attributes(title),
        }
        return {key: values for key, values in attributes.items() if values}

    @staticmethod
    def _split_attribute_values(raw_value: object) -> list[str]:
        if raw_value is None:
            return []
        values: list[str] = []
        seen: set[str] = set()
        fragments = raw_value if isinstance(raw_value, list) else _ATTRIBUTE_SPLIT_RE.split(str(raw_value))
        for fragment in fragments:
            value = " ".join(fragment.strip().split())
            normalized = value.casefold()
            if not value or len(value) > 80 or normalized in seen:
                continue
            seen.add(normalized)
            values.append(value)
            if len(values) >= 8:
                break
        return values

    @staticmethod
    def _infer_directional_attribute(
        title: str,
        token_labels: dict[str, str],
    ) -> list[str]:
        lowered = title.casefold()
        return [label for token, label in token_labels.items() if token in lowered]

    @staticmethod
    def _infer_feature_attributes(title: str) -> list[str]:
        normalized = " ".join(title.casefold().replace("/", " / ").split())
        feature_patterns = (
            (r"\b(?:com|c\s*/?)\s*ar\s+condicionado\b", "Com ar condicionado"),
            (r"\b(?:sem|s\s*/?)\s*ar\s+condicionado\b", "Sem ar condicionado"),
            (r"\b(?:com|c\s*/?)\s*rol(?:amento)?\b", "Com rolamento"),
            (r"\b(?:sem|s\s*/?)\s*rol(?:amento)?\b", "Sem rolamento"),
        )
        return [
            label
            for pattern, label in feature_patterns
            if re.search(pattern, normalized)
        ]

def resolve_search_tools(
    *, settings: Settings, logger: logging.Logger, catalog: PreSearchCatalog | None = None,
) -> ToolsPort:
    fallback_tools: PostgresErpSearchTools | None = None
    if settings.erp_fallback_db_enabled:
        fallback_tools = PostgresErpSearchTools(
            settings=settings,
            logger=logger,
            conninfo=build_catalog_conninfo(settings),
            backend_name="local_fallback_postgres",
            catalog=catalog,
        )

    if settings.erp_db_enabled:
        logger.info(
            "search_tools_resolved",
            extra={
                "search_tools_backend": (
                    "erp_postgres_with_local_fallback"
                    if fallback_tools is not None
                    else "erp_postgres"
                ),
                "erp_db_host": settings.erp_db_host,
                "erp_db_port": settings.erp_db_port,
                "erp_db_name": settings.erp_db_name,
                "fallback_db_enabled": fallback_tools is not None,
            },
        )
        postgres_tools = PostgresErpSearchTools(
            settings=settings,
            logger=logger,
            catalog=catalog,
            backend_name="erp_postgres",
        )
        if fallback_tools is not None:
            return FallbackErpSearchTools(
                primary=postgres_tools,
                fallback=fallback_tools,
                logger=logger,
            )
        return postgres_tools

    if fallback_tools is not None:
        logger.info(
            "search_tools_resolved",
            extra={
                "search_tools_backend": "local_fallback_postgres",
                "fallback_db_host": settings.catalog_db_host,
                "fallback_db_port": settings.catalog_db_port,
                "fallback_db_name": settings.catalog_db_name,
            },
        )
        return fallback_tools

    logger.error(
        "search_tools_unconfigured",
        extra={
            "search_tools_backend": "none",
            "erp_db_enabled": settings.erp_db_enabled,
            "erp_fallback_db_enabled": settings.erp_fallback_db_enabled,
        },
    )
    raise RuntimeError(
        "Busca de pecas nao configurada: defina ERP_DB_ENABLED=true ou "
        "ERP_FALLBACK_DB_ENABLED=true."
    )
