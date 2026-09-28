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
    if head.endswith(("antes", "entes", "intes", "ontes", "untes")):
        return r"\m" + re.escape(head[:-1]) + r"s?\M"
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
    # Trace begins after the family/code identity filter.  Scanning every ERP
    # item for every request would make observability itself an outage risk.
    identity_filters: list[str] = []
    item_refinement_filters: list[str] = []
    blocked_heads: list[str] = []
    if normalized["part_query"]:
        family_name_match = f"{_identity('part_family')} = %(part_query_norm)s"
        if family_ids is None:
            identity_filters.append(family_name_match)
        else:
            identities = []
            for index, (group, subgroup) in enumerate(family_ids):
                params[f"family_group_{index}"] = group
                params[f"family_subgroup_{index}"] = subgroup
                identities.append(f"(cd_grupo = %(family_group_{index})s AND cd_subgrupo = %(family_subgroup_{index})s)")
            identity_filters.append("(" + " OR ".join(identities or ["FALSE"]) + ")")
            family_head_pattern = _family_head_pattern(normalized["part_query"])
            if require_family_title_identity and family_head_pattern:
                params["family_head_pattern"] = family_head_pattern
                identity_filters.append(
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
                    token_pattern = re.escape(token)
                    if token.endswith(("antes", "entes", "intes", "ontes", "untes")):
                        token_pattern = re.escape(token[:-1]) + "s?"
                    params[f"family_token_{index}"] = r"\m" + token_pattern + r"\M"
                    title_filters.append(
                        f"{_identity('candidate_title')} ~ %(family_token_{index})s"
                    )
                identity_filters.append("(" + " AND ".join(title_filters or ["FALSE"]) + ")")
        # A wrongly classified accessory cannot masquerade as the main part.
        accessory_heads = ("tampa", "tampas", "kit", "kits", "mangueira", "mangueiras", "suporte", "suportes", "reparo", "reparos")
        requested_words = set(normalized["part_query"].split())
        blocked_heads = [head for head in accessory_heads if head not in requested_words and head.rstrip('s') not in {word.rstrip('s') for word in requested_words}]
        if blocked_heads:
            params["accessory_head_pattern"] = r"^(?:" + "|".join(blocked_heads) + r")\M"
            item_refinement_filters.append(f"NOT ({_identity('candidate_title')} ~ %(accessory_head_pattern)s)")
    if criteria.part_code:
        identity_filters.append(
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
            item_refinement_filters.append(f"concat_ws(' ', nm_item, candidate_title) ILIKE %({key}_like)s")
    # An empty or vehicle-only request must not enumerate the inventory.
    if not (normalized["part_query"] or criteria.part_code):
        identity_filters.append("FALSE")

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
    # A requested attribute is a hard predicate on one application row.  Its
    # score component records the evidence used; it is deliberately not a
    # reward for attributes that happen to be present only in the title.
    score_components = {
        "part_code": 1.0 if criteria.part_code else 0.0,
        "family": 0.0 if criteria.part_code else 0.32,
        "vehicle_brand": 0.0 if criteria.part_code else 0.08 * bool(normalized["vehicle_brand"]),
        "vehicle_model": 0.0 if criteria.part_code else 0.16 * bool(normalized["vehicle_model"]),
        "vehicle_year": 0.0 if criteria.part_code else 0.08 * (criteria.vehicle_year is not None),
        "engine": 0.0 if criteria.part_code else 0.08 * bool(normalized["engine"]),
        "variant": 0.0 if criteria.part_code else 0.05 * bool(normalized["variant"]),
        "side": 0.0 if criteria.part_code else 0.03 * bool(criteria.side),
        "position": 0.0 if criteria.part_code else 0.04 * bool(criteria.position),
        "axle": 0.0 if criteria.part_code else 0.03 * bool(criteria.axle),
    }
    params.update({f"score_{name}": value for name, value in score_components.items()})
    params["preferred_product_brand_bonus"] = 0.0 if criteria.part_code else 0.08
    # Corroboration is a ranking hint only: titles never create application
    # eligibility. Restrict evidence to the segment naming the requested model.
    params["ranking_model_pattern"] = r"\m" + re.escape(normalized["vehicle_model"] or "") + r"\M"
    params["ranking_model_tail_pattern"] = params["ranking_model_pattern"] + r"(.*)$"
    params["ranking_variant_pattern"] = r"\m" + re.escape(normalized["variant"] or "") + r"\M"
    params["ranking_variant_exclusion_pattern"] = r"\m(exceto|menos|sem)\s+" + re.escape(normalized["variant"] or "") + r"\M"
    params["ranking_engine_pattern"] = (
        r"(^|[^[:alnum:].])" + re.escape(normalized["engine"] or "") + r"([^[:alnum:].]|$)"
    )
    params["ranking_evidence_enabled"] = bool(normalized["vehicle_model"] and not criteria.part_code)
    params["ranking_has_variant"] = bool(normalized["variant"])
    params["ranking_has_engine"] = bool(normalized["engine"])
    params["trace_limit"] = min(max(int(limit), 1), 50)
    params["item_refinement_fields"] = [
        key for key, value in (
            ("accessory_identity", bool(blocked_heads)),
            ("side", bool(criteria.side)),
            ("position", bool(criteria.position)),
            ("axle", bool(criteria.axle)),
        ) if value
    ]
    params["application_filter_fields"] = [
        key for key, value in (
            ("vehicle_brand", bool(normalized["vehicle_brand"])),
            ("vehicle_model", bool(normalized["vehicle_model"])),
            ("vehicle_year", criteria.vehicle_year is not None),
            ("engine", bool(normalized["engine"])),
            ("variant", bool(normalized["variant"])),
        ) if value
    ]
    # All ranking terms apply only after identity and application predicates pass.
    base_score = sum(score_components.values())
    params["base_score"] = base_score
    sql = f"""
        WITH identity_candidates AS MATERIALIZED (
            SELECT * FROM soccol.item_search_candidates
            WHERE {' AND '.join(identity_filters or ['FALSE'])}
        ), eligible_items AS MATERIALIZED (
            SELECT * FROM identity_candidates
            WHERE {' AND '.join(item_refinement_filters or ['TRUE'])}
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
        ), title_evidence AS (
            SELECT m.*, evidence.year_supported, evidence.year_conflict,
                evidence.variant_supported, evidence.variant_conflict, evidence.engine_supported,
                evidence.model_segments
            FROM matched_items m
            CROSS JOIN LATERAL (
                SELECT
                    COALESCE(bool_or(%(vehicle_year)s BETWEEN yr.start_year AND yr.end_year), FALSE) AS year_supported,
                    COALESCE(bool_and(%(vehicle_year)s NOT BETWEEN yr.start_year AND yr.end_year)
                        FILTER (WHERE yr.start_year IS NOT NULL), FALSE) AS year_conflict,
                    COALESCE(bool_or(%(ranking_has_variant)s
                        AND segment IS NOT NULL
                        AND {_identity('m.candidate_title')} ~ %(ranking_variant_pattern)s
                        AND {_identity('m.candidate_title')} !~ '\\m(exceto|menos|sem)\\M'), FALSE) AS variant_supported,
                    COALESCE(bool_or(%(ranking_has_variant)s AND segment IS NOT NULL AND {_identity('m.candidate_title')}
                        ~ %(ranking_variant_exclusion_pattern)s), FALSE) AS variant_conflict,
                    COALESCE(bool_or(%(ranking_has_engine)s AND segment ~ %(ranking_engine_pattern)s
                        AND segment !~ '\\m(exceto|menos|sem)\\M'), FALSE) AS engine_supported,
                    COALESCE(jsonb_agg(DISTINCT segment), '[]'::jsonb) AS model_segments
                FROM regexp_split_to_table({_identity('m.candidate_title')}, '\\s+-\\s+') AS segment
                LEFT JOIN LATERAL (
                    SELECT (years[1])::int AS start_year, (years[2])::int AS end_year
                    FROM regexp_matches(substring(segment FROM %(ranking_model_tail_pattern)s), '\\m((?:19|20)[0-9]{{2}})\\s*[/ -]\\s*((?:19|20)[0-9]{{2}})\\M', 'g') AS years
                    WHERE (years[1])::int <= (years[2])::int
                        AND segment !~ '\\m(exceto|menos|sem)\\M'
                ) yr ON TRUE
                WHERE %(ranking_evidence_enabled)s AND segment ~ %(ranking_model_pattern)s
            ) evidence
        ), ranking_components AS (
            SELECT *,
                CASE WHEN year_conflict THEN -0.16 WHEN year_supported THEN 0.04 ELSE 0.0 END AS title_year_score,
                CASE WHEN variant_conflict THEN -0.16 WHEN variant_supported THEN 0.02 ELSE 0.0 END AS title_variant_score,
                CASE WHEN engine_supported THEN 0.02 ELSE 0.0 END AS title_engine_score
            FROM title_evidence
        ), ranked AS (
            SELECT *,
                CASE WHEN %(has_preferred_product_brand)s
                    AND candidate_title ILIKE %(preferred_product_brand_like)s
                    THEN 0 ELSE 1 END AS preferred_product_brand_rank
                , %(base_score)s + title_year_score + title_variant_score + title_engine_score + CASE
                    WHEN %(has_preferred_product_brand)s
                     AND candidate_title ILIKE %(preferred_product_brand_like)s
                    THEN %(preferred_product_brand_bonus)s ELSE 0 END AS raw_score
            FROM ranking_components
        ), final_rows AS MATERIALIZED (
            SELECT *, row_number() OVER (
                ORDER BY raw_score DESC, preferred_product_brand_rank,
                    length(candidate_title), COALESCE(NULLIF(cd_item, ''), id_item::text)
            ) AS rank_position
            FROM ranked
            ORDER BY raw_score DESC, preferred_product_brand_rank,
                length(candidate_title), COALESCE(NULLIF(cd_item, ''), id_item::text)
            LIMIT %(limit)s
        ), rejected_candidates AS (
            SELECT COALESCE(NULLIF(c.cd_item, ''), c.id_item::text) AS item_code,
                c.candidate_title AS title,
                'item_refinement_filter' AS reason,
                to_jsonb(%(item_refinement_fields)s::text[]) AS reason_fields
            FROM identity_candidates c
            WHERE NOT EXISTS (SELECT 1 FROM eligible_items e WHERE e.id_item = c.id_item)
            UNION ALL
            SELECT COALESCE(NULLIF(c.cd_item, ''), c.id_item::text) AS item_code,
                c.candidate_title AS title,
                'application_filter' AS reason,
                to_jsonb(%(application_filter_fields)s::text[]) AS reason_fields
            FROM eligible_items c
            WHERE {str(needs_application).upper()}
              AND NOT EXISTS (
                SELECT 1 FROM soccol.item_search_applications a
                WHERE {' AND '.join(application_filters)}
              )
        ), search_trace AS (
            SELECT jsonb_build_object(
                'ranking_version', 'application_corroboration_v1',
                'raw_candidates_count', (SELECT count(*) FROM identity_candidates),
                'rejected_candidates_count', (SELECT count(*) FROM rejected_candidates),
                'filtered_candidates_count', (SELECT count(*) FROM ranked),
                'ranked_candidates_count', (SELECT count(*) FROM final_rows),
                'raw_candidates', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'item_id', raw.item_code, 'title', raw.candidate_title
                    ) ORDER BY raw.item_code)
                    FROM (
                        SELECT COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
                            candidate_title
                        FROM identity_candidates
                        ORDER BY COALESCE(NULLIF(cd_item, ''), id_item::text)
                        LIMIT %(trace_limit)s
                    ) raw
                ), '[]'::jsonb),
                'rejected_candidates', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'item_id', rejected.item_code, 'title', rejected.title,
                        'reason', rejected.reason, 'reason_fields', rejected.reason_fields
                    ) ORDER BY rejected.item_code)
                    FROM (
                        SELECT * FROM rejected_candidates
                        ORDER BY item_code
                        LIMIT %(trace_limit)s
                    ) rejected
                ), '[]'::jsonb),
                'filtered_candidates', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'item_id', filtered.item_code, 'title', filtered.candidate_title
                    ) ORDER BY filtered.raw_score DESC, filtered.item_code)
                    FROM (
                        SELECT COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
                            candidate_title, raw_score
                        FROM ranked
                        ORDER BY raw_score DESC, COALESCE(NULLIF(cd_item, ''), id_item::text)
                        LIMIT %(trace_limit)s
                    ) filtered
                ), '[]'::jsonb),
                'ranked_candidates', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'item_id', ranked_item.item_code, 'title', ranked_item.candidate_title,
                        'rank_position', ranked_item.rank_position,
                        'matched_applications', ranked_item.applications,
                        'ranking_evidence', jsonb_build_object(
                            'model_segments', ranked_item.model_segments,
                            'title_year_supported', ranked_item.year_supported,
                            'title_year_conflict', ranked_item.year_conflict,
                            'title_variant_supported', ranked_item.variant_supported,
                            'title_variant_conflict', ranked_item.variant_conflict,
                            'title_engine_supported', ranked_item.engine_supported
                        ),
                        'score', ROUND(LEAST(1.0, ranked_item.raw_score)::numeric, 4),
                        'score_breakdown', jsonb_build_object(
                            'part_code', %(score_part_code)s,
                            'family', %(score_family)s,
                            'vehicle_brand', %(score_vehicle_brand)s,
                            'vehicle_model', %(score_vehicle_model)s,
                            'vehicle_year', %(score_vehicle_year)s,
                            'engine', %(score_engine)s,
                            'variant', %(score_variant)s,
                            'side', %(score_side)s,
                            'position', %(score_position)s,
                            'axle', %(score_axle)s,
                            'title_year_corroboration', ranked_item.title_year_score,
                            'title_variant_corroboration', ranked_item.title_variant_score,
                            'title_engine_corroboration', ranked_item.title_engine_score,
                            'preferred_product_brand', CASE
                                WHEN ranked_item.preferred_product_brand_rank = 0
                                THEN %(preferred_product_brand_bonus)s ELSE 0 END,
                            'injection', 0.0,
                            'transmission', 0.0,
                            'commercial_attribute', 0.0,
                            'total', ROUND(LEAST(1.0, ranked_item.raw_score)::numeric, 4)
                        )
                    ) ORDER BY ranked_item.rank_position)
                    FROM (
                        SELECT COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
                            candidate_title, raw_score, preferred_product_brand_rank,
                            rank_position, applications, model_segments, year_supported,
                            year_conflict, variant_supported, variant_conflict, engine_supported,
                            title_year_score, title_variant_score, title_engine_score
                        FROM final_rows
                    ) ranked_item
                ), '[]'::jsonb)
            ) AS diagnostics
        )
        SELECT COALESCE(NULLIF(cd_item, ''), id_item::text) AS item_code,
            candidate_title AS title, applications,
            ROUND(LEAST(1.0, raw_score)::numeric, 4) AS score,
            trace.diagnostics AS search_diagnostics,
            rank_position
        FROM final_rows
        CROSS JOIN search_trace trace
        UNION ALL
        SELECT NULL::text AS item_code, NULL::text AS title, NULL::jsonb AS applications,
            NULL::numeric AS score, trace.diagnostics AS search_diagnostics,
            2147483647 AS rank_position
        FROM search_trace trace
        WHERE NOT EXISTS (SELECT 1 FROM final_rows)
        ORDER BY rank_position
    """
    return sql, params
