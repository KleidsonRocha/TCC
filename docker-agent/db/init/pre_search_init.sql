CREATE TABLE IF NOT EXISTS pre_search_brand (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_brand_alias (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES pre_search_brand(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_model (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES pre_search_brand(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed',
    UNIQUE (brand_id, name_normalized)
);

CREATE TABLE IF NOT EXISTS pre_search_model_alias (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES pre_search_model(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_part_group (
    id BIGSERIAL PRIMARY KEY,
    source_group_code INTEGER NULL UNIQUE,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_part_type (
    id BIGSERIAL PRIMARY KEY,
    part_group_id BIGINT NOT NULL REFERENCES pre_search_part_group(id) ON DELETE RESTRICT,
    source_subgroup_code INTEGER NULL,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed',
    UNIQUE (part_group_id, source_subgroup_code),
    UNIQUE (part_group_id, name_normalized)
);

CREATE TABLE IF NOT EXISTS pre_search_part_alias (
    id BIGSERIAL PRIMARY KEY,
    part_type_id BIGINT NOT NULL REFERENCES pre_search_part_type(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed',
    UNIQUE (part_type_id, alias_normalized)
);

CREATE TABLE IF NOT EXISTS pre_search_part_rule (
    part_type_id BIGINT PRIMARY KEY REFERENCES pre_search_part_type(id) ON DELETE CASCADE,
    is_generic BOOLEAN NOT NULL DEFAULT FALSE,
    needs_side BOOLEAN NOT NULL DEFAULT FALSE,
    needs_position BOOLEAN NOT NULL DEFAULT FALSE,
    needs_axle BOOLEAN NOT NULL DEFAULT FALSE,
    needs_engine BOOLEAN NOT NULL DEFAULT FALSE,
    needs_variant BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_engine_option (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES pre_search_model(id) ON DELETE CASCADE,
    engine_option TEXT NOT NULL,
    engine_configuration TEXT NULL,
    engine_displacement TEXT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    year_from INTEGER NULL,
    year_to INTEGER NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed',
    UNIQUE (model_id, engine_option, sort_order)
);

CREATE TABLE IF NOT EXISTS pre_search_invalid_slot_token (
    token TEXT PRIMARY KEY,
    token_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_part_code_pattern (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NULL REFERENCES pre_search_brand(id) ON DELETE SET NULL,
    pattern_regex TEXT NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_criteria_weight (
    criterion_key TEXT PRIMARY KEY,
    weight INTEGER NOT NULL CHECK (weight >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_decision_policy (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    min_score_to_search INTEGER NOT NULL DEFAULT 70 CHECK (min_score_to_search >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE INDEX IF NOT EXISTS ix_pre_search_brand_alias_norm ON pre_search_brand_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_model_alias_norm ON pre_search_model_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_part_group_norm ON pre_search_part_group(name_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_part_alias_norm ON pre_search_part_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_engine_model ON pre_search_engine_option(model_id, sort_order);

-- O catalogo de dominio e carregado exclusivamente dos CSVs versionados em
-- db/init/csv/. Nao manter seeds duplicados aqui para evitar drift.

INSERT INTO pre_search_invalid_slot_token (token, token_normalized) VALUES
('nao', 'nao'),
('none', 'none'),
('n/a', 'n/a'),
('desconhecido', 'desconhecido'),
('na', 'na'),
('null', 'null'),
('indefinido', 'indefinido'),
('-', '-')
ON CONFLICT (token) DO NOTHING;

INSERT INTO pre_search_criteria_weight (criterion_key, weight, is_active, updated_by) VALUES
('part_code', 100, TRUE, 'seed'),
('part_query', 45, TRUE, 'seed'),
('vehicle_model', 35, TRUE, 'seed'),
('vehicle_year', 20, TRUE, 'seed'),
('vehicle_brand', 15, TRUE, 'seed'),
('engine', 20, TRUE, 'seed'),
('side', 10, TRUE, 'seed'),
('position', 10, TRUE, 'seed'),
('axle', 10, TRUE, 'seed'),
('variant', 10, TRUE, 'seed'),
('quantity', 5, TRUE, 'seed')
ON CONFLICT (criterion_key) DO NOTHING;

INSERT INTO pre_search_decision_policy (id, min_score_to_search, is_active, updated_by)
VALUES (1, 70, TRUE, 'seed')
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION pre_search_normalize_text(value TEXT)
RETURNS TEXT AS $$
    SELECT NULLIF(
        REGEXP_REPLACE(
            TRANSLATE(
                LOWER(BTRIM(COALESCE(value, ''))),
                'áàãâäéèêëíìîïóòõôöúùûüçñýÿ',
                'aaaaaeeeeiiiiooooouuuucnyy'
            ),
            '\s+',
            ' ',
            'g'
        ),
        ''
    );
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION pre_search_load_catalog_from_csv(
    base_path TEXT DEFAULT '/docker-entrypoint-initdb.d/csv'
) RETURNS VOID AS $$
DECLARE
    has_grupo BOOLEAN;
    has_subgrupo BOOLEAN;
    has_rule BOOLEAN;
    has_brand BOOLEAN;
    has_model BOOLEAN;
    has_engine BOOLEAN;
    has_part_alias BOOLEAN;
    rule_header TEXT;
    part_alias_header TEXT;
BEGIN
    has_grupo := COALESCE((pg_stat_file(base_path || '/grupo.csv', true)).size, 0) > 0;
    has_subgrupo := COALESCE((pg_stat_file(base_path || '/subgrupo.csv', true)).size, 0) > 0;
    has_rule := COALESCE((pg_stat_file(base_path || '/pre_search_part_rule.csv', true)).size, 0) > 0;
    has_brand := COALESCE((pg_stat_file(base_path || '/vehicle_brand.csv', true)).size, 0) > 0;
    has_model := COALESCE((pg_stat_file(base_path || '/vehicle_model.csv', true)).size, 0) > 0;
    has_engine := COALESCE((pg_stat_file(base_path || '/engine_option.csv', true)).size, 0) > 0;
    has_part_alias := COALESCE((pg_stat_file(base_path || '/pre_search_part_alias.csv', true)).size, 0) > 0;

    IF NOT (has_grupo AND has_subgrupo AND has_rule AND has_brand AND has_model AND has_engine AND has_part_alias) THEN
        RAISE EXCEPTION
            'CSV bootstrap obrigatorio ausente em %. Esperado: grupo.csv, subgrupo.csv, pre_search_part_rule.csv, pre_search_part_alias.csv, vehicle_brand.csv, vehicle_model.csv e engine_option.csv.',
            base_path;
    END IF;

    rule_header := LOWER(COALESCE(SPLIT_PART(pg_read_file(base_path || '/pre_search_part_rule.csv', 0, 4000, true), E'\n', 1), ''));
    IF POSITION('cd_grupo' IN rule_header) = 0 THEN
        RAISE EXCEPTION 'pre_search_part_rule.csv deve conter coluna cd_grupo para chave composta (cd_grupo + part_type_id).';
    END IF;

    IF has_part_alias THEN
        part_alias_header := LOWER(COALESCE(SPLIT_PART(pg_read_file(base_path || '/pre_search_part_alias.csv', 0, 4000, true), E'\n', 1), ''));
        IF POSITION('cd_grupo' IN part_alias_header) = 0
           OR POSITION('cd_subgrupo' IN part_alias_header) = 0
           OR POSITION('alias' IN part_alias_header) = 0 THEN
            RAISE EXCEPTION 'pre_search_part_alias.csv deve conter colunas cd_grupo, cd_subgrupo e alias.';
        END IF;
    END IF;

    CREATE TEMP TABLE stg_grupo (
        cd_grupo INTEGER,
        nm_grupo TEXT,
        dt_atz TEXT,
        fl_ativo TEXT,
        ignora_atz_preco TEXT,
        dias_vencimento_atz_preco TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_subgrupo (
        cd_grupo INTEGER,
        cd_subgrupo INTEGER,
        nm_subgrupo TEXT,
        dt_atz TEXT,
        ignora_atz_preco TEXT,
        dias_vencimento_atz_preco TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_part_rule (
        cd_grupo INTEGER,
        part_type_id INTEGER,
        is_generic TEXT,
        needs_side TEXT,
        needs_position TEXT,
        needs_axle TEXT,
        needs_engine TEXT,
        needs_variant TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_brand (
        montadora TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_model (
        veiculo TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_engine (
        veiculo TEXT,
        nome_motor TEXT,
        configuracao_motor TEXT,
        ano_inicial TEXT,
        ano_final TEXT,
        cilindrada TEXT
    ) ON COMMIT DROP;

    CREATE TEMP TABLE stg_part_alias (
        cd_grupo INTEGER,
        cd_subgrupo INTEGER,
        alias TEXT
    ) ON COMMIT DROP;

    EXECUTE format(
        'COPY stg_grupo FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
        base_path || '/grupo.csv'
    );
    EXECUTE format(
        'COPY stg_subgrupo FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
        base_path || '/subgrupo.csv'
    );
    EXECUTE format(
        'COPY stg_part_rule FROM PROGRAM %L WITH (FORMAT text, DELIMITER '';'', NULL '''', ENCODING ''UTF8'')',
        'tail -n +2 ' || base_path || '/pre_search_part_rule.csv'
    );
    EXECUTE format(
        'COPY stg_brand FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
        base_path || '/vehicle_brand.csv'
    );
    EXECUTE format(
        'COPY stg_model FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
        base_path || '/vehicle_model.csv'
    );
    EXECUTE format(
        'COPY stg_engine FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
        base_path || '/engine_option.csv'
    );
    IF has_part_alias THEN
        EXECUTE format(
            'COPY stg_part_alias FROM %L WITH (FORMAT csv, HEADER true, ENCODING ''UTF8'')',
            base_path || '/pre_search_part_alias.csv'
        );
    END IF;

    IF EXISTS (
        SELECT 1
        FROM stg_part_rule pr
        LEFT JOIN stg_subgrupo ss
          ON ss.cd_grupo = pr.cd_grupo
         AND ss.cd_subgrupo = pr.part_type_id
        WHERE ss.cd_subgrupo IS NULL
    ) THEN
        RAISE EXCEPTION 'pre_search_part_rule.csv contem linhas sem correspondencia em subgrupo.csv para chave composta (cd_grupo + part_type_id).';
    END IF;

    TRUNCATE TABLE
        pre_search_part_code_pattern,
        pre_search_engine_option,
        pre_search_model_alias,
        pre_search_model,
        pre_search_brand_alias,
        pre_search_brand,
        pre_search_part_rule,
        pre_search_part_alias,
        pre_search_part_type,
        pre_search_part_group
    RESTART IDENTITY;

    INSERT INTO pre_search_part_group (
        source_group_code,
        name,
        name_normalized,
        is_active,
        updated_by
    )
    SELECT DISTINCT
        sg.cd_grupo,
        TRIM(sg.nm_grupo),
        pre_search_normalize_text(sg.nm_grupo),
        LOWER(COALESCE(TRIM(sg.fl_ativo), 's')) <> 'n',
        'seed_csv'
    FROM stg_grupo sg
    WHERE sg.cd_grupo IS NOT NULL
      AND sg.nm_grupo IS NOT NULL
      AND TRIM(sg.nm_grupo) <> ''
    ON CONFLICT (source_group_code) DO UPDATE
    SET name = EXCLUDED.name,
        name_normalized = EXCLUDED.name_normalized,
        is_active = EXCLUDED.is_active,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_part_type (
        part_group_id,
        source_subgroup_code,
        name,
        name_normalized,
        is_active,
        updated_by
    )
    SELECT
        pg.id,
        ss.cd_subgrupo,
        TRIM(ss.nm_subgrupo),
        pre_search_normalize_text(ss.nm_subgrupo),
        TRUE,
        'seed_csv'
    FROM stg_subgrupo ss
    JOIN pre_search_part_group pg
      ON pg.source_group_code = ss.cd_grupo
    WHERE ss.cd_subgrupo IS NOT NULL
      AND ss.nm_subgrupo IS NOT NULL
      AND TRIM(ss.nm_subgrupo) <> ''
    ON CONFLICT (part_group_id, source_subgroup_code) DO UPDATE
    SET name = EXCLUDED.name,
        name_normalized = EXCLUDED.name_normalized,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_part_alias (
        part_type_id,
        alias,
        alias_normalized,
        is_active,
        updated_by
    )
    SELECT
        pt.id,
        pt.name,
        pt.name_normalized,
        TRUE,
        'seed_csv'
    FROM pre_search_part_type pt
    ON CONFLICT (part_type_id, alias_normalized) DO UPDATE
    SET alias = EXCLUDED.alias,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    IF has_part_alias THEN
        WITH alias_rows AS (
            SELECT
                pt.id AS part_type_id,
                BTRIM(spa.alias) AS alias,
                pre_search_normalize_text(spa.alias) AS alias_normalized
            FROM stg_part_alias spa
            JOIN pre_search_part_group pg
              ON pg.source_group_code = spa.cd_grupo
            JOIN pre_search_part_type pt
              ON pt.part_group_id = pg.id
             AND pt.source_subgroup_code = spa.cd_subgrupo
            WHERE spa.alias IS NOT NULL
              AND BTRIM(spa.alias) <> ''
        ),
        deduplicated_alias_rows AS (
            SELECT DISTINCT ON (part_type_id, alias_normalized)
                part_type_id,
                alias,
                alias_normalized
            FROM alias_rows
            WHERE alias_normalized IS NOT NULL
              AND alias_normalized <> ''
            ORDER BY part_type_id, alias_normalized, alias
        )
        INSERT INTO pre_search_part_alias (
            part_type_id,
            alias,
            alias_normalized,
            is_active,
            updated_by
        )
        SELECT
            part_type_id,
            alias,
            alias_normalized,
            TRUE,
            'seed_csv'
        FROM deduplicated_alias_rows
        ON CONFLICT (part_type_id, alias_normalized) DO UPDATE
        SET alias = EXCLUDED.alias,
            is_active = TRUE,
            updated_at = NOW(),
            updated_by = EXCLUDED.updated_by;
    END IF;

    WITH rule_target AS (
        SELECT
            pt.id AS part_type_id,
            pr.is_generic,
            pr.needs_side,
            pr.needs_position,
            pr.needs_axle,
            pr.needs_engine,
            pr.needs_variant
        FROM stg_part_rule pr
        JOIN pre_search_part_group pg
          ON pg.source_group_code = pr.cd_grupo
        JOIN pre_search_part_type pt
          ON pt.part_group_id = pg.id
         AND pt.source_subgroup_code = pr.part_type_id
    )
    INSERT INTO pre_search_part_rule (
        part_type_id,
        is_generic,
        needs_side,
        needs_position,
        needs_axle,
        needs_engine,
        needs_variant,
        updated_by
    )
    SELECT DISTINCT
        rt.part_type_id,
        LOWER(COALESCE(TRIM(rt.is_generic), 'false')) = 'true',
        LOWER(COALESCE(TRIM(rt.needs_side), 'false')) = 'true',
        LOWER(COALESCE(TRIM(rt.needs_position), 'false')) = 'true',
        LOWER(COALESCE(TRIM(rt.needs_axle), 'false')) = 'true',
        LOWER(COALESCE(TRIM(rt.needs_engine), 'false')) = 'true',
        LOWER(COALESCE(TRIM(rt.needs_variant), 'false')) = 'true',
        'seed_csv'
    FROM rule_target rt
    ON CONFLICT (part_type_id) DO UPDATE
    SET is_generic = EXCLUDED.is_generic,
        needs_side = EXCLUDED.needs_side,
        needs_position = EXCLUDED.needs_position,
        needs_axle = EXCLUDED.needs_axle,
        needs_engine = EXCLUDED.needs_engine,
        needs_variant = EXCLUDED.needs_variant,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_brand (
        name,
        name_normalized,
        is_active,
        updated_by
    )
    SELECT DISTINCT
        TRIM(sb.montadora),
        pre_search_normalize_text(sb.montadora),
        TRUE,
        'seed_csv'
    FROM stg_brand sb
    WHERE sb.montadora IS NOT NULL
      AND TRIM(sb.montadora) <> ''
      AND TRIM(sb.montadora) <> '-'
    ON CONFLICT (name_normalized) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_brand_alias (
        brand_id,
        alias,
        alias_normalized,
        is_active,
        updated_by
    )
    SELECT
        b.id,
        b.name,
        b.name_normalized,
        TRUE,
        'seed_csv'
    FROM pre_search_brand b
    ON CONFLICT (alias_normalized) DO UPDATE
    SET brand_id = EXCLUDED.brand_id,
        alias = EXCLUDED.alias,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_brand (
        name,
        name_normalized,
        is_active,
        updated_by
    )
    VALUES ('SEM_MARCA_MAPEADA', 'sem_marca_mapeada', TRUE, 'seed_csv')
    ON CONFLICT (name_normalized) DO NOTHING;

    WITH normalized_model_seed AS (
        SELECT DISTINCT ON (pre_search_normalize_text(sm.veiculo))
            b.id AS brand_id,
            TRIM(sm.veiculo) AS model_name,
            pre_search_normalize_text(sm.veiculo) AS model_name_normalized
        FROM stg_model sm
        JOIN pre_search_brand b
          ON b.name_normalized = 'sem_marca_mapeada'
        WHERE sm.veiculo IS NOT NULL
          AND TRIM(sm.veiculo) <> ''
          AND TRIM(sm.veiculo) NOT IN ('-', '--')
          AND TRIM(sm.veiculo) !~ '^\(.*\)$'
        ORDER BY
            pre_search_normalize_text(sm.veiculo),
            LENGTH(TRIM(sm.veiculo)),
            TRIM(sm.veiculo)
    )
    INSERT INTO pre_search_model (
        brand_id,
        name,
        name_normalized,
        is_active,
        updated_by
    )
    SELECT
        nms.brand_id,
        nms.model_name,
        nms.model_name_normalized,
        TRUE,
        'seed_csv'
    FROM normalized_model_seed nms
    ON CONFLICT (brand_id, name_normalized) DO UPDATE
    SET name = EXCLUDED.name,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    INSERT INTO pre_search_model_alias (
        model_id,
        alias,
        alias_normalized,
        is_active,
        updated_by
    )
    SELECT
        m.id,
        m.name,
        m.name_normalized,
        TRUE,
        'seed_csv'
    FROM pre_search_model m
    ON CONFLICT (alias_normalized) DO UPDATE
    SET model_id = EXCLUDED.model_id,
        alias = EXCLUDED.alias,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    WITH normalized_model_alias_seed AS (
        SELECT DISTINCT ON (pre_search_normalize_text(sm.veiculo))
            m.id AS model_id,
            TRIM(sm.veiculo) AS alias,
            pre_search_normalize_text(sm.veiculo) AS alias_normalized
        FROM stg_model sm
        JOIN pre_search_model m
          ON m.name_normalized = pre_search_normalize_text(sm.veiculo)
        WHERE sm.veiculo IS NOT NULL
          AND TRIM(sm.veiculo) <> ''
          AND TRIM(sm.veiculo) NOT IN ('-', '--')
          AND TRIM(sm.veiculo) !~ '^\(.*\)$'
        ORDER BY
            pre_search_normalize_text(sm.veiculo),
            LENGTH(TRIM(sm.veiculo)),
            TRIM(sm.veiculo)
    )
    INSERT INTO pre_search_model_alias (
        model_id,
        alias,
        alias_normalized,
        is_active,
        updated_by
    )
    SELECT
        nmas.model_id,
        nmas.alias,
        nmas.alias_normalized,
        TRUE,
        'seed_csv'
    FROM normalized_model_alias_seed nmas
    ON CONFLICT (alias_normalized) DO UPDATE
    SET model_id = EXCLUDED.model_id,
        alias = EXCLUDED.alias,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    WITH mapped_engine AS (
        SELECT
            m.id AS model_id,
            COALESCE(
                NULLIF(TRIM(se.nome_motor), '-'),
                NULLIF(TRIM(se.configuracao_motor), '-'),
                NULLIF(TRIM(se.cilindrada), '-')
            ) AS engine_option,
            NULLIF(TRIM(se.configuracao_motor), '-') AS engine_configuration,
            NULLIF(TRIM(se.cilindrada), '-') AS engine_displacement,
            CASE
                WHEN COALESCE(se.ano_inicial, '') ~ '(19|20)[0-9]{2}'
                    THEN SUBSTRING(se.ano_inicial FROM '(19|20)[0-9]{2}')::INTEGER
                ELSE NULL
            END AS year_from,
            CASE
                WHEN COALESCE(se.ano_final, '') ~ '(19|20)[0-9]{2}'
                    THEN SUBSTRING(se.ano_final FROM '(19|20)[0-9]{2}')::INTEGER
                ELSE NULL
            END AS year_to
        FROM stg_engine se
        JOIN pre_search_model m
          ON m.name_normalized = pre_search_normalize_text(se.veiculo)
        WHERE se.veiculo IS NOT NULL
          AND TRIM(se.veiculo) <> ''
          AND TRIM(se.veiculo) NOT IN ('-', '--')
          AND TRIM(se.veiculo) !~ '^\(.*\)$'
    ),
    ranked_engine AS (
        SELECT
            me.model_id,
            me.engine_option,
            me.engine_configuration,
            me.engine_displacement,
            CASE
                WHEN me.year_from IS NOT NULL
                    AND me.year_to IS NOT NULL
                    AND me.year_to < me.year_from
                    THEN me.year_to
                ELSE me.year_from
            END AS year_from,
            CASE
                WHEN me.year_from IS NOT NULL
                    AND me.year_to IS NOT NULL
                    AND me.year_to < me.year_from
                    THEN me.year_from
                ELSE me.year_to
            END AS year_to,
            ROW_NUMBER() OVER (
                PARTITION BY me.model_id
                ORDER BY me.engine_option, me.year_from NULLS LAST, me.year_to NULLS LAST
            ) AS sort_order
        FROM mapped_engine me
        WHERE me.engine_option IS NOT NULL
          AND TRIM(me.engine_option) <> ''
    )
    INSERT INTO pre_search_engine_option (
        model_id,
        engine_option,
        engine_configuration,
        engine_displacement,
        sort_order,
        year_from,
        year_to,
        is_active,
        updated_by
    )
    SELECT
        re.model_id,
        re.engine_option,
        re.engine_configuration,
        re.engine_displacement,
        re.sort_order,
        re.year_from,
        re.year_to,
        TRUE,
        'seed_csv'
    FROM ranked_engine re
    ON CONFLICT (model_id, engine_option, sort_order) DO UPDATE
    SET engine_configuration = EXCLUDED.engine_configuration,
        engine_displacement = EXCLUDED.engine_displacement,
        year_from = EXCLUDED.year_from,
        year_to = EXCLUDED.year_to,
        is_active = TRUE,
        updated_at = NOW(),
        updated_by = EXCLUDED.updated_by;

    RAISE NOTICE 'CSV bootstrap concluido em %.', base_path;
END;
$$ LANGUAGE plpgsql;

SELECT pre_search_load_catalog_from_csv();
DROP FUNCTION pre_search_load_catalog_from_csv(TEXT);
DROP FUNCTION pre_search_normalize_text(TEXT);

INSERT INTO pre_search_part_code_pattern (brand_id, pattern_regex, description)
VALUES
(NULL, '\y[A-Za-z]{2,5}[- ]?\d{3,8}\y', 'Padrao generico de codigo de peca')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS pre_search_fine_tuning_dataset_header (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NULL,
    task_type TEXT NOT NULL DEFAULT 'pre_search_validation',
    output_schema_version TEXT NOT NULL DEFAULT '1.0',
    base_model_hint TEXT NULL,
    system_prompt_override TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_fine_tuning_dataset_record (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES pre_search_fine_tuning_dataset_header(id) ON DELETE CASCADE,
    example_key TEXT NOT NULL,
    data_split TEXT NOT NULL CHECK (data_split IN ('train', 'validation', 'test')),
    input_message_text TEXT NOT NULL,
    input_last_messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_decision TEXT NOT NULL CHECK (expected_decision IN ('search', 'ask', 'handoff')),
    expected_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_next_question JSONB NULL,
    expected_confidence NUMERIC(4,3) NOT NULL DEFAULT 0.950 CHECK (expected_confidence >= 0 AND expected_confidence <= 1),
    part_code_source TEXT NOT NULL DEFAULT 'none' CHECK (part_code_source IN ('literal', 'context_literal', 'none')),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT NULL,
    include_in_fine_tune BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed',
    UNIQUE (dataset_id, example_key),
    CHECK (jsonb_typeof(input_last_messages) = 'array'),
    CHECK (jsonb_typeof(expected_criteria) = 'object'),
    CHECK (jsonb_typeof(expected_items) = 'array'),
    CHECK (jsonb_typeof(expected_missing_fields) = 'array'),
    CHECK (expected_next_question IS NULL OR jsonb_typeof(expected_next_question) = 'object'),
    CHECK (jsonb_typeof(tags) = 'array'),
    CHECK (
        (expected_decision = 'ask' AND expected_next_question IS NOT NULL)
        OR (expected_decision <> 'ask' AND expected_next_question IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS pre_search_fine_tuning_run (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES pre_search_fine_tuning_dataset_header(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    base_model TEXT NOT NULL,
    target_model_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'exported', 'submitted', 'running', 'completed', 'failed', 'archived')),
    data_export_dir TEXT NULL,
    train_file_path TEXT NULL,
    validation_file_path TEXT NULL,
    notes TEXT NULL,
    started_at TIMESTAMPTZ NULL,
    finished_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE INDEX IF NOT EXISTS ix_pre_search_ft_dataset_record_dataset_split
    ON pre_search_fine_tuning_dataset_record(dataset_id, data_split)
    WHERE is_active AND include_in_fine_tune;

ALTER TABLE pre_search_fine_tuning_dataset_record
    ADD COLUMN IF NOT EXISTS expected_items JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_pre_search_ft_run_dataset
    ON pre_search_fine_tuning_run(dataset_id, status);

CREATE OR REPLACE VIEW pre_search_fine_tuning_dataset_record_export AS
SELECT
    ds.slug AS dataset_slug,
    ds.name AS dataset_name,
    ds.description AS dataset_description,
    ds.task_type,
    ds.output_schema_version,
    ds.base_model_hint,
    ds.system_prompt_override,
    ex.id AS example_id,
    ex.example_key,
    ex.data_split,
    ex.input_message_text,
    ex.input_last_messages,
    ex.expected_decision,
    ex.expected_criteria,
    ex.expected_missing_fields,
    ex.expected_next_question,
    ex.expected_confidence,
    ex.part_code_source,
    ex.tags,
    ex.notes,
    ex.expected_items
FROM pre_search_fine_tuning_dataset_header ds
JOIN pre_search_fine_tuning_dataset_record ex
  ON ex.dataset_id = ds.id
WHERE ds.is_active
  AND ex.is_active
  AND ex.include_in_fine_tune;

INSERT INTO pre_search_fine_tuning_dataset_header (
    slug,
    name,
    description,
    base_model_hint,
    updated_by
)
VALUES (
    'pre-search-ft-v1',
    'Pre-search Fine-tuning v1',
    'Dataset seed para ensinar a LLM a decidir search/ask/handoff, evitar part_code inventado e manter o contrato JSON do pre-search.',
    'qwen2.5:7b',
    'seed'
)
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    base_model_hint = EXCLUDED.base_model_hint,
    updated_at = NOW(),
    updated_by = EXCLUDED.updated_by;

WITH dataset_target AS (
    SELECT id
    FROM pre_search_fine_tuning_dataset_header
    WHERE slug = 'pre-search-ft-v1'
),
seed_rows AS (
    SELECT *
    FROM (
        VALUES
            (
                'train_ask_no_part',
                'train',
                'preciso de uma peca',
                '[]',
                'ask',
                '{}',
                '["part_query"]',
                '{"type":"request_info","key":"part_query","prompt":"Qual peca voce precisa?"}',
                0.980,
                'none',
                '["ask","missing_part_query"]',
                'Caso basico: sem part_query e sem part_code deve perguntar a peca.'
            ),
            (
                'train_search_explicit_part_code',
                'train',
                'codigo AB-1234',
                '[]',
                'search',
                '{"part_code":"AB-1234"}',
                '[]',
                NULL,
                0.990,
                'literal',
                '["search","part_code"]',
                'part_code literal deve acionar search sem invencao adicional.'
            ),
            (
                'train_ask_radiador_engine',
                'train',
                'radiador gol 2010',
                '[]',
                'ask',
                '{"part_query":"radiador","vehicle_model":"Gol","vehicle_year":2010}',
                '["engine"]',
                '{"type":"request_info","key":"engine","prompt":"Qual a motorizacao do veiculo?","options":["1.0","1.6","Nao sei"]}',
                0.970,
                'none',
                '["ask","engine"]',
                'Nao pode virar handoff; falta objetiva de engine deve gerar ask.'
            ),
            (
                'train_search_radiador_engine',
                'train',
                'radiador gol 2010 1.6',
                '[]',
                'search',
                '{"part_query":"radiador","vehicle_model":"Gol","vehicle_year":2010,"engine":"1.6"}',
                '[]',
                NULL,
                0.990,
                'none',
                '["search","engine"]',
                'Com engine presente a resposta deve ser search.'
            ),
            (
                'train_ask_bandeja_side',
                'train',
                'bandeja ecosport 2008',
                '[]',
                'ask',
                '{"part_query":"bandeja","vehicle_model":"Ecosport","vehicle_year":2008}',
                '["side"]',
                '{"type":"request_info","key":"side","prompt":"Qual o lado da peca?","options":["esquerdo","direito"]}',
                0.960,
                'none',
                '["ask","side"]',
                'Bandeja exige lado no catalogo seed.'
            ),
            (
                'train_search_bandeja_side',
                'train',
                'bandeja ecosport 2008 lado esquerdo',
                '[]',
                'search',
                '{"part_query":"bandeja","vehicle_model":"Ecosport","vehicle_year":2008,"side":"left"}',
                '[]',
                NULL,
                0.980,
                'none',
                '["search","side"]',
                'Com lado resolvido a busca pode acontecer.'
            ),
            (
                'train_ask_correia_dentada_engine',
                'train',
                'correia de comando gol 2010',
                '[]',
                'ask',
                '{"part_query":"correia dentada","vehicle_model":"Gol","vehicle_year":2010}',
                '["engine"]',
                '{"type":"request_info","key":"engine","prompt":"Qual a motorizacao do veiculo?","options":["1.0","1.6","Nao sei"]}',
                0.950,
                'none',
                '["ask","engine","no_part_code_hallucination"]',
                'Nao transformar modelo+ano em part_code. O correto e ask por engine.'
            ),
            (
                'train_search_context_engine',
                'train',
                '1.6',
                '[{"role":"user","text":"radiador gol 2010"},{"role":"assistant","text":"Qual a motorizacao do veiculo?"}]',
                'search',
                '{"part_query":"radiador","vehicle_model":"Gol","vehicle_year":2010,"engine":"1.6"}',
                '[]',
                NULL,
                0.980,
                'none',
                '["search","context"]',
                'A resposta curta deve herdar o contexto e concluir search.'
            ),
            (
                'train_ask_context_year_then_side',
                'train',
                '2008',
                '[{"role":"user","text":"bandeja ecosport"},{"role":"assistant","text":"Qual o ano do veiculo?"}]',
                'ask',
                '{"part_query":"bandeja","vehicle_model":"Ecosport","vehicle_year":2008}',
                '["side"]',
                '{"type":"request_info","key":"side","prompt":"Qual o lado da peca?","options":["esquerdo","direito"]}',
                0.950,
                'none',
                '["ask","context"]',
                'Depois de completar o ano, a proxima pergunta util ainda e sobre side.'
            ),
            (
                'train_handoff_out_of_scope',
                'train',
                'quero ajuda com financiamento do carro',
                '[]',
                'handoff',
                '{}',
                '[]',
                NULL,
                0.900,
                'none',
                '["handoff","out_of_scope"]',
                'Caso realmente fora do dominio de autopecas.'
            ),
            (
                'validation_ask_pastilha_position',
                'validation',
                'pastilha gol 2010',
                '[]',
                'ask',
                '{"part_query":"pastilha de freio","vehicle_model":"Gol","vehicle_year":2010}',
                '["position"]',
                '{"type":"request_info","key":"position","prompt":"A peca e dianteira ou traseira?","options":["dianteira","traseira"]}',
                0.960,
                'none',
                '["validation","ask","position"]',
                'Validacao de peca que depende de posicao.'
            ),
            (
                'validation_search_pastilha_position',
                'validation',
                'pastilha gol 2010 dianteira',
                '[]',
                'search',
                '{"part_query":"pastilha de freio","vehicle_model":"Gol","vehicle_year":2010,"position":"front"}',
                '[]',
                NULL,
                0.980,
                'none',
                '["validation","search","position"]',
                'Validacao de slot position completo.'
            ),
            (
                'validation_reject_model_year_as_part_code',
                'validation',
                'preciso do radiador gol-2010',
                '[]',
                'ask',
                '{"part_query":"radiador","vehicle_model":"Gol","vehicle_year":2010}',
                '["engine"]',
                '{"type":"request_info","key":"engine","prompt":"Qual a motorizacao do veiculo?","options":["1.0","1.6","Nao sei"]}',
                0.940,
                'none',
                '["validation","no_part_code_hallucination"]',
                'Mesmo com hifen, gol-2010 nao e part_code.'
            )
    ) AS rows(
        example_key,
        data_split,
        input_message_text,
        input_last_messages,
        expected_decision,
        expected_criteria,
        expected_missing_fields,
        expected_next_question,
        expected_confidence,
        part_code_source,
        tags,
        notes
    )
)
INSERT INTO pre_search_fine_tuning_dataset_record (
    dataset_id,
    example_key,
    data_split,
    input_message_text,
    input_last_messages,
    expected_decision,
    expected_criteria,
    expected_missing_fields,
    expected_next_question,
    expected_confidence,
    part_code_source,
    tags,
    notes,
    include_in_fine_tune,
    is_active,
    updated_by
)
SELECT
    dt.id,
    sr.example_key,
    sr.data_split,
    sr.input_message_text,
    sr.input_last_messages::jsonb,
    sr.expected_decision,
    sr.expected_criteria::jsonb,
    sr.expected_missing_fields::jsonb,
    CASE
        WHEN sr.expected_next_question IS NULL THEN NULL
        ELSE sr.expected_next_question::jsonb
    END,
    sr.expected_confidence,
    sr.part_code_source,
    sr.tags::jsonb,
    sr.notes,
    TRUE,
    TRUE,
    'seed'
FROM dataset_target dt
JOIN seed_rows sr ON TRUE
ON CONFLICT (dataset_id, example_key) DO UPDATE
SET data_split = EXCLUDED.data_split,
    input_message_text = EXCLUDED.input_message_text,
    input_last_messages = EXCLUDED.input_last_messages,
    expected_decision = EXCLUDED.expected_decision,
    expected_criteria = EXCLUDED.expected_criteria,
    expected_missing_fields = EXCLUDED.expected_missing_fields,
    expected_next_question = EXCLUDED.expected_next_question,
    expected_confidence = EXCLUDED.expected_confidence,
    part_code_source = EXCLUDED.part_code_source,
    tags = EXCLUDED.tags,
    notes = EXCLUDED.notes,
    include_in_fine_tune = EXCLUDED.include_in_fine_tune,
    is_active = EXCLUDED.is_active,
    updated_at = NOW(),
    updated_by = EXCLUDED.updated_by;

CREATE TABLE IF NOT EXISTS pre_search_review_interaction (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    branch_id INTEGER NOT NULL,
    channel_name TEXT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    message_text TEXT NOT NULL,
    last_messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    predicted_decision TEXT NOT NULL CHECK (predicted_decision IN ('search', 'ask', 'handoff')),
    predicted_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,
    predicted_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    predicted_missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    predicted_next_question JSONB NULL,
    predicted_confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (predicted_confidence >= 0 AND predicted_confidence <= 1),
    final_reply_text TEXT NOT NULL,
    final_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_handoff_required BOOLEAN NOT NULL DEFAULT FALSE,
    final_handoff_reason TEXT NULL,
    final_confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (final_confidence >= 0 AND final_confidence <= 1),
    final_used_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    search_query TEXT NULL,
    llm_model TEXT NOT NULL,
    llm_num_predict INTEGER NOT NULL DEFAULT 220,
    llm_endpoint_used TEXT NULL,
    llm_raw_content TEXT NULL,
    llm_output_valid BOOLEAN NULL,
    llm_parse_error TEXT NULL,
    llm_fallback_used BOOLEAN NULL,
    llm_decision_raw TEXT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'reviewed', 'promoted', 'discarded')),
    review_priority_score INTEGER NOT NULL DEFAULT 0,
    reviewed_decision TEXT NULL CHECK (reviewed_decision IS NULL OR reviewed_decision IN ('search', 'ask', 'handoff')),
    reviewed_criteria JSONB NULL,
    reviewed_items JSONB NULL,
    reviewed_missing_fields JSONB NULL,
    reviewed_question_key TEXT NULL,
    reviewed_question_prompt TEXT NULL,
    reviewed_question_options JSONB NULL,
    reviewed_notes TEXT NULL,
    reviewed_by TEXT NULL,
    reviewed_at TIMESTAMPTZ NULL,
    promoted_dataset_slug TEXT NULL,
    promoted_example_key TEXT NULL,
    promoted_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(last_messages) = 'array'),
    CHECK (jsonb_typeof(predicted_criteria) = 'object'),
    CHECK (jsonb_typeof(predicted_items) = 'array'),
    CHECK (jsonb_typeof(predicted_missing_fields) = 'array'),
    CHECK (predicted_next_question IS NULL OR jsonb_typeof(predicted_next_question) = 'object'),
    CHECK (jsonb_typeof(final_actions) = 'array'),
    CHECK (jsonb_typeof(final_used_tools) = 'array'),
    CHECK (reviewed_criteria IS NULL OR jsonb_typeof(reviewed_criteria) = 'object'),
    CHECK (reviewed_items IS NULL OR jsonb_typeof(reviewed_items) = 'array'),
    CHECK (reviewed_missing_fields IS NULL OR jsonb_typeof(reviewed_missing_fields) = 'array'),
    CHECK (reviewed_question_options IS NULL OR jsonb_typeof(reviewed_question_options) = 'array'),
    CHECK (
        reviewed_decision IS DISTINCT FROM 'ask'
        OR (reviewed_question_key IS NOT NULL AND reviewed_question_prompt IS NOT NULL)
    )
);

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_endpoint_used TEXT NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_raw_content TEXT NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_output_valid BOOLEAN NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_parse_error TEXT NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_fallback_used BOOLEAN NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS llm_decision_raw TEXT NULL;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS predicted_items JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE pre_search_review_interaction
    ADD COLUMN IF NOT EXISTS reviewed_items JSONB NULL;

CREATE TABLE IF NOT EXISTS pre_search_review_revision (
    id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT NOT NULL REFERENCES pre_search_review_interaction(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('reviewed', 'discarded', 'reopened')),
    previous_status TEXT NULL,
    snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    changed_by TEXT NOT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(snapshot) = 'object')
);

CREATE INDEX IF NOT EXISTS ix_pre_search_review_revision_interaction
    ON pre_search_review_revision(interaction_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_pre_search_review_status_priority
    ON pre_search_review_interaction(review_status, review_priority_score DESC, created_at ASC);

CREATE INDEX IF NOT EXISTS ix_pre_search_review_conversation
    ON pre_search_review_interaction(conversation_id, created_at DESC);

CREATE OR REPLACE VIEW pre_search_review_queue AS
SELECT
    id,
    created_at,
    trace_id,
    conversation_id,
    branch_id,
    channel_name,
    message_text,
    predicted_decision,
    predicted_confidence,
    predicted_missing_fields,
    predicted_next_question,
    final_handoff_required,
    final_handoff_reason,
    llm_model,
    llm_num_predict,
    llm_endpoint_used,
    llm_output_valid,
    llm_fallback_used,
    llm_decision_raw,
    review_status,
    review_priority_score,
    reviewed_decision,
    reviewed_question_key,
    reviewed_question_prompt,
    promoted_dataset_slug,
    promoted_example_key,
    predicted_items,
    reviewed_items
FROM pre_search_review_interaction
WHERE review_status IN ('pending', 'reviewed')
ORDER BY review_priority_score DESC, created_at ASC;

ALTER TABLE pre_search_fine_tuning_run
    ADD COLUMN IF NOT EXISTS benchmark_summary JSONB NULL;

ALTER TABLE pre_search_fine_tuning_run
    ADD COLUMN IF NOT EXISTS promotion_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (promotion_status IN ('pending', 'rejected', 'promoted'));

ALTER TABLE pre_search_fine_tuning_run
    ADD COLUMN IF NOT EXISTS promoted_env_file TEXT NULL;

ALTER TABLE pre_search_fine_tuning_run
    ADD COLUMN IF NOT EXISTS promotion_applied_at TIMESTAMPTZ NULL;
