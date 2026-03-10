\set ON_ERROR_STOP on

BEGIN;

DROP TABLE IF EXISTS pre_search_part_code_pattern CASCADE;
DROP TABLE IF EXISTS pre_search_engine_option CASCADE;
DROP TABLE IF EXISTS pre_search_part_rule CASCADE;
DROP TABLE IF EXISTS pre_search_part_alias CASCADE;
DROP TABLE IF EXISTS pre_search_part_type CASCADE;
DROP TABLE IF EXISTS pre_search_model_alias CASCADE;
DROP TABLE IF EXISTS pre_search_model CASCADE;
DROP TABLE IF EXISTS pre_search_brand_alias CASCADE;
DROP TABLE IF EXISTS pre_search_brand CASCADE;
DROP TABLE IF EXISTS pre_search_invalid_slot_token CASCADE;

\i /docker-entrypoint-initdb.d/001_pre_search_catalog.sql

COMMIT;

