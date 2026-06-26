\echo 'Initializing local ERP fallback search table from CSV'

CREATE SCHEMA IF NOT EXISTS soccol;

DROP TABLE IF EXISTS soccol.item_search_candidates;

CREATE TABLE soccol.item_search_candidates (
    id_item BIGINT,
    cd_item TEXT,
    nm_item TEXT,
    candidate_title TEXT,
    cd_grupo INTEGER,
    cd_subgrupo INTEGER,
    cd_tipo TEXT,
    cd_class_fiscal TEXT,
    cd_linha_produto TEXT,
    cd_marca TEXT,
    cd_original TEXT,
    cd_fabricante TEXT,
    vehicle_year_start INTEGER,
    vehicle_year_end INTEGER,
    vehicle_year_open_end BOOLEAN,
    vehicle_brand_codes TEXT,
    vehicle_model_codes TEXT,
    vehicle_brand_names TEXT,
    vehicle_model_names TEXT,
    vehicle_complement_codes TEXT,
    vehicle_complement_names TEXT,
    vehicle_application_complement_text TEXT,
    vehicle_model_complement_codes TEXT,
    vehicle_model_complement_names TEXT,
    vehicle_model_injection_codes TEXT,
    vehicle_model_injection_names TEXT,
    vehicle_model_motor_codes TEXT,
    vehicle_model_motor_names TEXT,
    vehicle_model_transmission_codes TEXT,
    vehicle_model_transmission_names TEXT,
    vehicle_application_text TEXT,
    vehicle_relation_keys TEXT,
    similar_codes_text TEXT,
    search_text TEXT
);

COPY soccol.item_search_candidates (
    id_item,
    cd_item,
    nm_item,
    candidate_title,
    cd_grupo,
    cd_subgrupo,
    cd_tipo,
    cd_class_fiscal,
    cd_linha_produto,
    cd_marca,
    cd_original,
    cd_fabricante,
    vehicle_year_start,
    vehicle_year_end,
    vehicle_year_open_end,
    vehicle_brand_codes,
    vehicle_model_codes,
    vehicle_brand_names,
    vehicle_model_names,
    vehicle_complement_codes,
    vehicle_complement_names,
    vehicle_application_complement_text,
    vehicle_model_complement_codes,
    vehicle_model_complement_names,
    vehicle_model_injection_codes,
    vehicle_model_injection_names,
    vehicle_model_motor_codes,
    vehicle_model_motor_names,
    vehicle_model_transmission_codes,
    vehicle_model_transmission_names,
    vehicle_application_text,
    vehicle_relation_keys,
    similar_codes_text,
    search_text
)
FROM '/docker-entrypoint-initdb.d/fallback/item_search_candidates.csv'
WITH (FORMAT csv, HEADER true, NULL '', QUOTE '"', ESCAPE '"');

CREATE INDEX IF NOT EXISTS ix_item_search_candidates_cd_item_lower
    ON soccol.item_search_candidates (LOWER(cd_item));

CREATE INDEX IF NOT EXISTS ix_item_search_candidates_cd_original_lower
    ON soccol.item_search_candidates (LOWER(cd_original));

CREATE INDEX IF NOT EXISTS ix_item_search_candidates_cd_fabricante_lower
    ON soccol.item_search_candidates (LOWER(cd_fabricante));

CREATE INDEX IF NOT EXISTS ix_item_search_candidates_vehicle_year
    ON soccol.item_search_candidates (vehicle_year_start, vehicle_year_end);

ANALYZE soccol.item_search_candidates;
