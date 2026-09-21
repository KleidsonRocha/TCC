"""SQL contract v2: identify the family, then match one vehicle application."""

import re

from app.core.domain.pre_search import SearchCriteria
from app.infra.pre_search_text import (
    longitudinal_direction_search_fragment,
    normalize_pre_search_text,
)


def _identity(expression: str) -> str:
    # Same Portuguese accent/case/whitespace normalization as the catalog.
    return (
        "translate(lower(regexp_replace(btrim(" + expression + "), "
        "'\\s+', ' ', 'g')), "
        "'áàâãäéèêëíìîïóòôõöúùûüçñ', 'aaaaaeeeeiiiiooooouuuucn')"
    )


def _literal_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _family_head_pattern(part_query: str) -> str | None:
    tokens = [
        token for token in part_query.split()
        if token not in {"de", "do", "da", "dos", "das", "e"}
    ]
    if not tokens:
        return None
    head = tokens[0]
    if head in {"coxim", "coxins"}:
        return r"\mcoxi[mn]\M"
    if head.endswith("ores") and len(head) > 5:
        head = head[:-2]
    elif head.endswith("es") and len(head) > 4:
        head = head[:-2]
    elif head.endswith("s") and len(head) > 3:
        head = head[:-1]
    return r"\m" + re.escape(head) + r"\M"


def build_search_sql(
    *, criteria: SearchCriteria, limit: int,
    family_ids: list[tuple[int, int]] | None = None,
    require_family_title_identity: bool = False,
) -> tuple[str, dict[str, object]]:
    """No title, aggregate year envelope or model-wide attribute proves fitment."""
    normalized = {
        key: normalize_pre_search_text(value) if value else None
        for key, value in {
            "part_query": criteria.part_query,
            "vehicle_brand": criteria.vehicle_brand,
            "vehicle_model": criteria.vehicle_model,
            "engine": criteria.engine,
            "variant": criteria.variant,
        }.items()
    }
    params: dict[str, object] = {
        **{key + "_norm": value for key, value in normalized.items()},
        "part_query": normalized["part_query"],
        "part_code_norm": criteria.part_code.strip().lower() if criteria.part_code else None,
        "vehicle_year": criteria.vehicle_year,
        "limit": limit,
    }
    item_filters = []
    if normalized["part_query"]:
        family_name_match = f"{_identity('part_family')} = %(part_query_norm)s"
        if family_ids is None:
            item_filters.append(family_name_match)
        else:
            identities = []
            for index, (group, subgroup) in enumerate(family_ids):
                params[f"family_group_{index}"] = group
                params[f"family_subgroup_{index}"] = subgroup
                identities.append(f"(cd_grupo = %(family_group_{index})s AND cd_subgrupo = %(family_subgroup_{index})s)")
            item_filters.append("(" + " OR ".join(identities or ["FALSE"]) + ")")
            family_head_pattern = _family_head_pattern(normalized["part_query"])
            if require_family_title_identity and family_head_pattern:
                params["family_head_pattern"] = family_head_pattern
                item_filters.append(
                    f"{_identity('candidate_title')} ~ %(family_head_pattern)s"
                )
            # One curated ERP group/subgroup pair is a complete family
            # identity.  When a specialized family spans several broad ERP
            # subgroups, require its canonical words in the title as a second
            # identity proof (for example, coxim de amortecedor vs. motor).
            if len(family_ids) > 1:
                title_filters = []
                for index, token in enumerate(normalized["part_query"].split()):
                    if token in {"de", "do", "da", "dos", "das", "e"}:
                        continue
                    params[f"family_token_{index}"] = r"\m" + re.escape(token) + r"\M"
                    title_filters.append(
                        f"{_identity('candidate_title')} ~ %(family_token_{index})s"
                    )
                item_filters.append("(" + " AND ".join(title_filters or ["FALSE"]) + ")")
        # A wrongly classified accessory cannot masquerade as the main part.
        accessory_heads = ("tampa", "tampas", "kit", "kits", "mangueira", "mangueiras", "suporte", "suportes", "reparo", "reparos")
        requested_words = set(normalized["part_query"].split())
        blocked_heads = [head for head in accessory_heads if head not in requested_words and head.rstrip('s') not in {word.rstrip('s') for word in requested_words}]
        if blocked_heads:
            params["accessory_head_pattern"] = r"^(?:" + "|".join(blocked_heads) + r")\M"
            item_filters.append(f"NOT ({_identity('candidate_title')} ~ %(accessory_head_pattern)s)")
    if criteria.part_code:
        item_filters.append(
            "(lower(cd_item) = %(part_code_norm)s "
            "OR lower(cd_original) = %(part_code_norm)s "
            "OR lower(cd_fabricante) = %(part_code_norm)s)"
        )
    # The full item name can contain direction omitted from its display title.
    # Neither field contains another vehicle's application text.
    for key, fragment in {
        "side": {"left": "esquerd", "right": "direit"}.get(criteria.side or ""),
        "position": longitudinal_direction_search_fragment(criteria.position),
        "axle": {"front": "eixo dianteiro", "rear": "eixo traseiro"}.get(criteria.axle or ""),
    }.items():
        params["has_" + key] = bool(fragment)
        if fragment:
            params[key + "_like"] = "%" + fragment + "%"
            item_filters.append(f"concat_ws(' ', nm_item, candidate_title) ILIKE %({key}_like)s")
    # An empty or vehicle-only request must not enumerate the inventory.
    if not (normalized["part_query"] or criteria.part_code):
        item_filters.append("FALSE")

    application_filters = ["a.id_item = c.id_item"]
    for key in ("vehicle_brand", "vehicle_model"):
        if normalized[key]:
            application_filters.append(f"{_identity('a.' + key)} = %({key}_norm)s")
    if criteria.vehicle_year is not None:
        application_filters.append(
            "(a.year_start IS NOT NULL AND a.year_start <= %(vehicle_year)s "
            "AND ((a.year_open_end IS TRUE AND a.year_end IS NULL) "
            "OR (a.year_open_end IS FALSE AND a.year_end >= %(vehicle_year)s)))"
        )
    if normalized["engine"]:
        # A displacement can be a token in '1.0 L 8V FLEX'; never in '11.0'.
        params["engine_pattern"] = (
            r"(^|[^[:alnum:].])" + re.escape(normalized["engine"])
            + r"([^[:alnum:].]|$)"
        )
        application_filters.append(
            "EXISTS (SELECT 1 FROM unnest(a.engines) AS engine_name "
            f"WHERE {_identity('engine_name')} ~ %(engine_pattern)s)"
        )
    if normalized["variant"]:
        application_filters.append(
            "EXISTS (SELECT 1 FROM unnest(a.variants) AS variant_name "
            f"WHERE {_identity('variant_name')} = %(variant_norm)s)"
        )
    engine_values = (
        "ARRAY(SELECT engine_name FROM unnest(a.engines) AS engine_name "
        f"WHERE {_identity('engine_name')} ~ %(engine_pattern)s)"
        if normalized["engine"] else "a.engines"
    )
    variant_values = (
        "ARRAY(SELECT variant_name FROM unnest(a.variants) AS variant_name "
        f"WHERE {_identity('variant_name')} = %(variant_norm)s)"
        if normalized["variant"] else "a.variants"
    )
    needs_application = len(application_filters) > 1
    preferred_brand = (criteria.preferred_product_brand or "").strip()
    params["has_preferred_product_brand"] = bool(preferred_brand)
    params["preferred_product_brand_like"] = "%" + _literal_like(preferred_brand) + "%"
    # All ranking terms apply only after identity and application predicates pass.
    base_score = 1.0 if criteria.part_code else (
        0.32
        + 0.08 * bool(normalized["vehicle_brand"])
        + 0.16 * bool(normalized["vehicle_model"])
        + 0.08 * (criteria.vehicle_year is not None)
        + 0.08 * bool(normalized["engine"])
        + 0.05 * bool(normalized["variant"])
        + 0.03 * bool(criteria.side)
        + 0.04 * bool(criteria.position)
        + 0.03 * bool(criteria.axle)
    )
    params["base_score"] = base_score
    sql = f"""
        WITH eligible_items AS MATERIALIZED (
            SELECT * FROM soccol.item_search_candidates
            WHERE {' AND '.join(item_filters)}
        ), matched_items AS (
            SELECT c.*, matched.applications
            FROM eligible_items c
            CROSS JOIN LATERAL (
                SELECT jsonb_agg(jsonb_build_object(
                    'application_id', a.application_id,
                    'vehicle_brand', a.vehicle_brand,
                    'vehicle_model', a.vehicle_model,
                    'year_start', a.year_start, 'year_end', a.year_end,
                    'year_open_end', a.year_open_end,
                    'engines', {engine_values}, 'variants', {variant_values},
                    'injections', a.injections, 'transmissions', a.transmissions
                ) ORDER BY a.application_id) AS applications
                FROM soccol.item_search_applications a
                WHERE {' AND '.join(application_filters)}
            ) matched
            WHERE {'matched.applications IS NOT NULL' if needs_application else 'TRUE'}
        ), ranked AS (
            SELECT *,
                CASE WHEN %(has_preferred_product_brand)s
                    AND candidate_title ILIKE %(preferred_product_brand_like)s
                    THEN 0 ELSE 1 END AS preferred_product_brand_rank
            FROM matched_items
        )
        SELECT COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
            candidate_title AS title, applications,
            ROUND(LEAST(1.0, %(base_score)s + CASE
                WHEN preferred_product_brand_rank = 0 THEN 0.08 ELSE 0 END)::numeric, 4) AS score
        FROM ranked
        ORDER BY score DESC, preferred_product_brand_rank, length(candidate_title), item_code
        LIMIT %(limit)s
    """
    return sql, params
