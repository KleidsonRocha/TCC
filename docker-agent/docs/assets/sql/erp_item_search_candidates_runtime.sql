-- ERP candidate search runtime v2
-- Use this when the direct single-view version is functionally correct but too slow.
--
-- Strategy:
-- 1. Pre-aggregate vehicle dimensions by model
-- 2. Pre-aggregate vehicle relations by item
-- 3. Materialize the final candidate dataset with only runtime-relevant columns
-- 4. Expose a stable wrapper view at soccol.item_search_candidates

-- Optional but recommended for text search later.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP VIEW IF EXISTS soccol.item_search_candidates;
DROP MATERIALIZED VIEW IF EXISTS soccol.item_search_candidates_mv;
DROP MATERIALIZED VIEW IF EXISTS soccol.item_vehicle_agg_mv;
DROP MATERIALIZED VIEW IF EXISTS soccol.item_vehicle_model_agg_mv;

CREATE MATERIALIZED VIEW soccol.item_vehicle_model_agg_mv AS
WITH vehicle_model_dim AS (
    SELECT
        vm.cd_modelo,
        vm.nm_modelo,
        vm.cd_montadora,
        vmt.nm_montadora
    FROM public.veiculo_modelo vm
    LEFT JOIN public.veiculo_montadora vmt
        ON vmt.cd_montadora = vm.cd_montadora
),
vehicle_complement_dim AS (
    SELECT
        vc.cd_complemento,
        vc.nm_complemento
    FROM public.veiculo_complemento vc
),
vehicle_injection_dim AS (
    SELECT
        vi.cd_injecao,
        vi.nm_injecao
    FROM public.veiculo_injecao vi
),
vehicle_motor_dim AS (
    SELECT
        vm.cd_motor,
        vm.nm_motor
    FROM public.veiculo_motor vm
),
vehicle_transmission_dim AS (
    SELECT
        vt.cd_transmissao,
        vt.nm_transmissao
    FROM public.veiculo_transmissao vt
),
vehicle_model_complement_agg AS (
    SELECT
        vmc.cd_modelo,
        STRING_AGG(DISTINCT vmc.cd_complemento::text, ' ')
            FILTER (WHERE vmc.cd_complemento IS NOT NULL) AS model_complement_codes,
        STRING_AGG(DISTINCT NULLIF(btrim(vcd.nm_complemento), ''), ' | ')
            FILTER (WHERE NULLIF(btrim(vcd.nm_complemento), '') IS NOT NULL) AS model_complement_names
    FROM public.veiculo_modelo_complemento vmc
    LEFT JOIN vehicle_complement_dim vcd
        ON vcd.cd_complemento = vmc.cd_complemento
    GROUP BY vmc.cd_modelo
),
vehicle_model_injection_agg AS (
    SELECT
        vmi.cd_modelo,
        STRING_AGG(DISTINCT vmi.cd_injecao::text, ' ')
            FILTER (WHERE vmi.cd_injecao IS NOT NULL) AS model_injection_codes,
        STRING_AGG(DISTINCT NULLIF(btrim(vid.nm_injecao), ''), ' | ')
            FILTER (WHERE NULLIF(btrim(vid.nm_injecao), '') IS NOT NULL) AS model_injection_names
    FROM public.veiculo_modelo_injecao vmi
    LEFT JOIN vehicle_injection_dim vid
        ON vid.cd_injecao = vmi.cd_injecao
    GROUP BY vmi.cd_modelo
),
vehicle_model_motor_agg AS (
    SELECT
        vmm.cd_modelo,
        STRING_AGG(DISTINCT vmm.cd_motor::text, ' ')
            FILTER (WHERE vmm.cd_motor IS NOT NULL) AS model_motor_codes,
        STRING_AGG(DISTINCT NULLIF(btrim(vmdm.nm_motor), ''), ' | ')
            FILTER (WHERE NULLIF(btrim(vmdm.nm_motor), '') IS NOT NULL) AS model_motor_names
    FROM public.veiculo_modelo_motor vmm
    LEFT JOIN vehicle_motor_dim vmdm
        ON vmdm.cd_motor = vmm.cd_motor
    GROUP BY vmm.cd_modelo
),
vehicle_model_transmission_agg AS (
    SELECT
        vmt.cd_modelo,
        STRING_AGG(DISTINCT vmt.cd_transmissao::text, ' ')
            FILTER (WHERE vmt.cd_transmissao IS NOT NULL) AS model_transmission_codes,
        STRING_AGG(DISTINCT NULLIF(btrim(vtd.nm_transmissao), ''), ' | ')
            FILTER (WHERE NULLIF(btrim(vtd.nm_transmissao), '') IS NOT NULL) AS model_transmission_names
    FROM public.veiculo_modelo_transmissao vmt
    LEFT JOIN vehicle_transmission_dim vtd
        ON vtd.cd_transmissao = vmt.cd_transmissao
    GROUP BY vmt.cd_modelo
)
SELECT
    vmd.cd_modelo,
    vmd.cd_montadora,
    vmd.nm_montadora,
    vmd.nm_modelo,
    vmca.model_complement_codes,
    vmca.model_complement_names,
    vmia.model_injection_codes,
    vmia.model_injection_names,
    vmma.model_motor_codes,
    vmma.model_motor_names,
    vmta.model_transmission_codes,
    vmta.model_transmission_names
FROM vehicle_model_dim vmd
LEFT JOIN vehicle_model_complement_agg vmca
    ON vmca.cd_modelo = vmd.cd_modelo
LEFT JOIN vehicle_model_injection_agg vmia
    ON vmia.cd_modelo = vmd.cd_modelo
LEFT JOIN vehicle_model_motor_agg vmma
    ON vmma.cd_modelo = vmd.cd_modelo
LEFT JOIN vehicle_model_transmission_agg vmta
    ON vmta.cd_modelo = vmd.cd_modelo;

CREATE UNIQUE INDEX ix_item_vehicle_model_agg_mv_cd_modelo
    ON soccol.item_vehicle_model_agg_mv (cd_modelo);

CREATE INDEX ix_item_vehicle_model_agg_mv_cd_montadora
    ON soccol.item_vehicle_model_agg_mv (cd_montadora);

CREATE MATERIALIZED VIEW soccol.item_vehicle_agg_mv AS
WITH vehicle_complement_dim AS (
    SELECT
        vc.cd_complemento,
        vc.nm_complemento
    FROM public.veiculo_complemento vc
)
SELECT
    pv.id_item,
    MIN(NULLIF(pv.ano_inicial, 0)) AS vehicle_year_start,
    MAX(NULLIF(pv.ano_final, 0)) AS vehicle_year_end,
    BOOL_OR(COALESCE(pv.ano_final, 0) = 0) AS vehicle_year_open_end,
    STRING_AGG(DISTINCT pv.cd_montadora::text, ' | ')
        FILTER (WHERE pv.cd_montadora IS NOT NULL) AS vehicle_brand_codes,
    STRING_AGG(DISTINCT pv.cd_modelo::text, ' | ')
        FILTER (WHERE pv.cd_modelo IS NOT NULL) AS vehicle_model_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.nm_montadora), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.nm_montadora), '') IS NOT NULL) AS vehicle_brand_names,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.nm_modelo), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.nm_modelo), '') IS NOT NULL) AS vehicle_model_names,
    STRING_AGG(DISTINCT pv.cd_complemento::text, ' | ')
        FILTER (WHERE pv.cd_complemento IS NOT NULL) AS vehicle_complement_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(vcd.nm_complemento), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(vcd.nm_complemento), '') IS NOT NULL) AS vehicle_complement_names,
    STRING_AGG(DISTINCT NULLIF(btrim(pv.complemento), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(pv.complemento), '') IS NOT NULL) AS vehicle_application_complement_text,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_complement_codes), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_complement_codes), '') IS NOT NULL) AS vehicle_model_complement_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_complement_names), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_complement_names), '') IS NOT NULL) AS vehicle_model_complement_names,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_injection_codes), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_injection_codes), '') IS NOT NULL) AS vehicle_model_injection_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_injection_names), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_injection_names), '') IS NOT NULL) AS vehicle_model_injection_names,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_motor_codes), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_motor_codes), '') IS NOT NULL) AS vehicle_model_motor_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_motor_names), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_motor_names), '') IS NOT NULL) AS vehicle_model_motor_names,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_transmission_codes), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_transmission_codes), '') IS NOT NULL) AS vehicle_model_transmission_codes,
    STRING_AGG(DISTINCT NULLIF(btrim(ivm.model_transmission_names), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(ivm.model_transmission_names), '') IS NOT NULL) AS vehicle_model_transmission_names,
    STRING_AGG(DISTINCT NULLIF(btrim(pv.aplicacao), ''), ' | ')
        FILTER (WHERE NULLIF(btrim(pv.aplicacao), '') IS NOT NULL) AS vehicle_application_text,
    STRING_AGG(
        DISTINCT CONCAT_WS(
            ' ',
            pv.cd_montadora::text,
            pv.cd_modelo::text,
            NULLIF(btrim(pv.complemento), '')
        ),
        ' | '
    ) FILTER (
        WHERE pv.cd_montadora IS NOT NULL
           OR pv.cd_modelo IS NOT NULL
           OR NULLIF(btrim(pv.complemento), '') IS NOT NULL
    ) AS vehicle_relation_keys
FROM public.produto_veiculos pv
LEFT JOIN soccol.item_vehicle_model_agg_mv ivm
    ON ivm.cd_modelo = pv.cd_modelo
LEFT JOIN vehicle_complement_dim vcd
    ON vcd.cd_complemento = pv.cd_complemento
GROUP BY pv.id_item;

CREATE UNIQUE INDEX ix_item_vehicle_agg_mv_id_item
    ON soccol.item_vehicle_agg_mv (id_item);

CREATE INDEX ix_item_vehicle_agg_mv_year_range
    ON soccol.item_vehicle_agg_mv (vehicle_year_start, vehicle_year_end);

CREATE MATERIALIZED VIEW soccol.item_search_candidates_mv AS
WITH item_produto_clean AS (
    SELECT
        ip.id_item,
        MAX(ip.cd_marca) AS cd_marca,
        MAX(NULLIF(btrim(ip.cd_original), '')) AS cd_original,
        MAX(NULLIF(btrim(ip.cd_fabricante), '')) AS cd_fabricante
    FROM public.item_produto ip
    GROUP BY ip.id_item
),
item_pesquisa_clean AS (
    SELECT
        ip.id_item,
        NULLIF(btrim(ip.item_concat), '') AS item_concat,
        NULLIF(btrim(ip.codigos_barras), '') AS codigos_barras,
        NULLIF(btrim(ip.outros_codigos_similares), '') AS outros_codigos_similares,
        NULLIF(btrim(ip.aplicacoes_veiculos), '') AS aplicacoes_veiculos,
        NULLIF(btrim(ip.marca_grupos), '') AS marca_grupos,
        NULLIF(btrim(ip.pesquisa_full_text_txt), '') AS pesquisa_full_text_txt
    FROM public.item_pesquisa ip
),
similar_codes_agg AS (
    SELECT
        gsi.id_item,
        STRING_AGG(DISTINCT NULLIF(btrim(gsoc.codigo), ''), ' ')
            FILTER (WHERE NULLIF(btrim(gsoc.codigo), '') IS NOT NULL) AS similar_codes_text
    FROM public.grupo_similar_item gsi
    LEFT JOIN public.grupo_similar_outros_codigos gsoc
        ON gsoc.cd_grupo_similar_item = gsi.cd_grupo_similar_item
    GROUP BY gsi.id_item
)
SELECT
    i.id_item,
    i.cd_item,
    i.nm_item,
    COALESCE(NULLIF(btrim(i.nm_reduzido), ''), i.nm_item) AS candidate_title,
    i.cd_grupo,
    i.cd_subgrupo,
    i.cd_tipo,
    i.cd_class_fiscal,
    i.cd_linha_produto,
    ipc.cd_marca,
    ipc.cd_original,
    ipc.cd_fabricante,
    iva.vehicle_year_start,
    iva.vehicle_year_end,
    iva.vehicle_year_open_end,
    iva.vehicle_brand_codes,
    iva.vehicle_model_codes,
    iva.vehicle_brand_names,
    iva.vehicle_model_names,
    iva.vehicle_complement_codes,
    iva.vehicle_complement_names,
    iva.vehicle_application_complement_text,
    iva.vehicle_model_complement_codes,
    iva.vehicle_model_complement_names,
    iva.vehicle_model_injection_codes,
    iva.vehicle_model_injection_names,
    iva.vehicle_model_motor_codes,
    iva.vehicle_model_motor_names,
    iva.vehicle_model_transmission_codes,
    iva.vehicle_model_transmission_names,
    iva.vehicle_application_text,
    iva.vehicle_relation_keys,
    sca.similar_codes_text,
    NULLIF(
        btrim(
            regexp_replace(
                CONCAT_WS(
                    ' ',
                    i.cd_item,
                    i.nm_item,
                    i.nm_reduzido,
                    ipc.cd_original,
                    ipc.cd_fabricante,
                    ipsc.codigos_barras,
                    ipsc.item_concat,
                    ipsc.outros_codigos_similares,
                    ipsc.aplicacoes_veiculos,
                    iva.vehicle_brand_names,
                    iva.vehicle_model_names,
                    iva.vehicle_complement_names,
                    iva.vehicle_application_complement_text,
                    iva.vehicle_model_injection_names,
                    iva.vehicle_model_motor_names,
                    iva.vehicle_model_transmission_names,
                    iva.vehicle_application_text,
                    sca.similar_codes_text,
                    ipsc.marca_grupos
                ),
                E'\\s+',
                ' ',
                'g'
            )
        ),
        ''
    ) AS search_text
FROM public.item i
LEFT JOIN item_produto_clean ipc
    ON ipc.id_item = i.id_item
LEFT JOIN item_pesquisa_clean ipsc
    ON ipsc.id_item = i.id_item
LEFT JOIN soccol.item_vehicle_agg_mv iva
    ON iva.id_item = i.id_item
LEFT JOIN similar_codes_agg sca
    ON sca.id_item = i.id_item
WHERE i.fl_ativo = 'S'
  AND i.cd_tipo <> '07';

CREATE UNIQUE INDEX ix_item_search_candidates_mv_id_item
    ON soccol.item_search_candidates_mv (id_item);

CREATE INDEX ix_item_search_candidates_mv_cd_item
    ON soccol.item_search_candidates_mv (cd_item);

CREATE INDEX ix_item_search_candidates_mv_year_range
    ON soccol.item_search_candidates_mv (vehicle_year_start, vehicle_year_end);

CREATE INDEX ix_item_search_candidates_mv_search_text_trgm
    ON soccol.item_search_candidates_mv
    USING gin (search_text gin_trgm_ops);

CREATE INDEX ix_item_search_candidates_mv_brand_names_trgm
    ON soccol.item_search_candidates_mv
    USING gin (vehicle_brand_names gin_trgm_ops);

CREATE INDEX ix_item_search_candidates_mv_model_names_trgm
    ON soccol.item_search_candidates_mv
    USING gin (vehicle_model_names gin_trgm_ops);

CREATE OR REPLACE VIEW soccol.item_search_candidates AS
SELECT *
FROM soccol.item_search_candidates_mv;

-- Refresh order after source data changes:
-- REFRESH MATERIALIZED VIEW soccol.item_vehicle_model_agg_mv;
-- REFRESH MATERIALIZED VIEW soccol.item_vehicle_agg_mv;
-- REFRESH MATERIALIZED VIEW soccol.item_search_candidates_mv;
