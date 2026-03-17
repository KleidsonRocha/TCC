# ERP Candidate Search View

This guide describes a first ERP-side view for candidate retrieval.

Use this in the ERP database, not in the local `docker-agent` catalog database.

Suggested object name:
- `soccol.item_search_candidates`

## Goal

The first real search integration should return only candidate items:
- `item_id`
- display title
- search score calculated by the query

This first cut should not bring:
- pricing
- stock
- taxation
- WMS
- technical detail enrichment

That enrichment can be a second query after the item list is known.

## Why A View

The ERP search data is spread across multiple tables:
- `item`
- `item_produto`
- `produto_veiculos`
- `item_pesquisa`
- `grupo_similar_item`
- `grupo_similar_outros_codigos`

If the `docker-agent` queries those tables directly, the integration becomes too coupled to ERP internals.

The view gives one candidate row per `id_item`, already flattening:
- item code and names
- brand and model dimensions from ERP vehicle tables
- product codes
- vehicle application text
- year range
- vehicle complement, injection, motor and transmission codes
- similar codes
- auxiliary search text

## Proposed View

SQL file:
- [erp_item_search_candidates_view.sql](/d:/TCC/docker-agent/docs/assets/sql/erp_item_search_candidates_view.sql:1)

Runtime-oriented version:
- [erp_item_search_candidates_runtime_v2.sql](/d:/TCC/docker-agent/docs/assets/sql/erp_item_search_candidates_runtime_v2.sql:1)

Output fields worth using in the first integration:
- `id_item`
- `cd_item`
- `candidate_title`
- `cd_original`
- `cd_fabricante`
- `vehicle_brand_names`
- `vehicle_model_names`
- `vehicle_complement_names`
- `vehicle_model_injection_names`
- `vehicle_model_motor_names`
- `vehicle_model_transmission_names`
- `vehicle_year_start`
- `vehicle_year_end`
- `vehicle_year_open_end`
- `vehicle_application_text`
- `similar_codes_text`
- `search_text`
- `pesquisa_full_text_txt`

## Practical Notes

- `item_produto.obs_ficha_tecnica` and `item_pesquisa.ficha_tecnica_item` are cleaned from HTML so they can be reused later.
- `produto_veiculos` is aggregated so the view keeps one row per item.
- `veiculo_montadora` and `veiculo_modelo` are resolved into brand/model names.
- `grupo_similar_outros_codigos` is aggregated into a single text field.
- `veiculo_complemento`, `veiculo_injecao`, `veiculo_motor` and `veiculo_transmissao` are resolved into readable names.
- the relation tables by model still remain exposed as aggregated codes and names.
- The view already excludes inactive items and items with `cd_tipo = '07'`.

## Example Search Query

Example for:
- part: `coxim`
- model: `ecosport`
- year: `2008`

```sql
WITH params AS (
    SELECT
        'coxim'::text AS part_query,
        'ford'::text AS vehicle_brand,
        'ecosport'::text AS vehicle_model,
        '1.6'::text AS vehicle_engine,
        2008::int AS vehicle_year
)
SELECT
    v.id_item,
    v.cd_item,
    v.candidate_title,
    (
        CASE
            WHEN v.cd_item ILIKE '%' || p.part_query || '%' THEN 0.35
            WHEN v.search_text ILIKE '%' || p.part_query || '%' THEN 0.25
            ELSE 0
        END
        +
        CASE
            WHEN COALESCE(v.vehicle_brand_names, '') ILIKE '%' || p.vehicle_brand || '%' THEN 0.15
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_brand || '%' THEN 0.10
            ELSE 0
        END
        +
        CASE
            WHEN COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.30
            WHEN COALESCE(v.vehicle_model_names, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.25
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.20
            ELSE 0
        END
        +
        CASE
            WHEN p.vehicle_engine IS NULL THEN 0
            WHEN COALESCE(v.vehicle_model_motor_names, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.20
            WHEN COALESCE(v.vehicle_application_text, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.15
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.10
            ELSE 0
        END
        +
        CASE
            WHEN p.vehicle_year IS NULL THEN 0
            WHEN (
                p.vehicle_year >= COALESCE(v.vehicle_year_start, 1900)
                AND (
                    v.vehicle_year_open_end
                    OR p.vehicle_year <= COALESCE(v.vehicle_year_end, 2100)
                )
            ) THEN 0.25
            WHEN COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_year::text || '%' THEN 0.15
            ELSE 0
        END
    ) AS score
FROM soccol.item_search_candidates v
CROSS JOIN params p
WHERE v.search_text ILIKE '%' || p.part_query || '%'
  AND (
      p.vehicle_brand IS NULL
      OR COALESCE(v.vehicle_brand_names, '') ILIKE '%' || p.vehicle_brand || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_brand || '%'
  )
  AND (
      COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_model || '%'
      OR COALESCE(v.vehicle_model_names, '') ILIKE '%' || p.vehicle_model || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_model || '%'
  )
  AND (
      p.vehicle_engine IS NULL
      OR COALESCE(v.vehicle_model_motor_names, '') ILIKE '%' || p.vehicle_engine || '%'
      OR COALESCE(v.vehicle_application_text, '') ILIKE '%' || p.vehicle_engine || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_engine || '%'
  )
ORDER BY score DESC, v.id_item
LIMIT 20;
```

## Naming

The guide now assumes:
- schema: `soccol`
- object name: `item_search_candidates`

So the expected usage is:

```sql
SELECT * FROM soccol.item_search_candidates LIMIT 10;
```

## Important Limitation

If you want `pg_trgm` indexes later, a plain `VIEW` is not the best final target.

For performance, the likely progression is:
1. start with this `VIEW`
2. validate search quality
3. if needed, move to:
   - a `MATERIALIZED VIEW`, or
   - a dedicated ERP search table refreshed periodically

That is the right place for heavier indexing and trigram search.

## Runtime Recommendation

If the single-view version is too slow in the ERP, use the runtime v2 SQL:
- [erp_item_search_candidates_runtime_v2.sql](/d:/TCC/docker-agent/docs/assets/sql/erp_item_search_candidates_runtime_v2.sql:1)

It changes the design to:
1. `soccol.item_vehicle_model_agg_mv`
2. `soccol.item_vehicle_agg_mv`
3. `soccol.item_search_candidates_mv`
4. `soccol.item_search_candidates` as a thin wrapper view

This reduces repeated aggregation over `produto_veiculos` and allows indexes on the final search dataset.

Refresh order:

```sql
REFRESH MATERIALIZED VIEW soccol.item_vehicle_model_agg_mv;
REFRESH MATERIALIZED VIEW soccol.item_vehicle_agg_mv;
REFRESH MATERIALIZED VIEW soccol.item_search_candidates_mv;
```

## What Is Still Missing

This proposal already resolves official brand/model names through:
- `veiculo_montadora`
- `veiculo_modelo`

What is still missing is only the business decision of how much each new dimension should weigh in ranking:
- complement
- injection
- motor
- transmission

The view now exposes both codes and readable names for these dimensions.
