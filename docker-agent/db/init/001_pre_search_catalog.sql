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

CREATE TABLE IF NOT EXISTS pre_search_part_type (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    category_name TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_part_alias (
    id BIGSERIAL PRIMARY KEY,
    part_type_id BIGINT NOT NULL REFERENCES pre_search_part_type(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_part_rule (
    part_type_id BIGINT PRIMARY KEY REFERENCES pre_search_part_type(id) ON DELETE CASCADE,
    is_generic BOOLEAN NOT NULL DEFAULT FALSE,
    needs_side BOOLEAN NOT NULL DEFAULT FALSE,
    needs_position BOOLEAN NOT NULL DEFAULT FALSE,
    needs_engine BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS pre_search_engine_option (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES pre_search_model(id) ON DELETE CASCADE,
    engine_option TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS ix_pre_search_brand_alias_norm ON pre_search_brand_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_model_alias_norm ON pre_search_model_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_part_alias_norm ON pre_search_part_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS ix_pre_search_engine_model ON pre_search_engine_option(model_id, sort_order);

INSERT INTO pre_search_brand (name, name_normalized) VALUES
('Ford', 'ford'),
('Chevrolet', 'chevrolet'),
('Volkswagen', 'volkswagen'),
('Fiat', 'fiat'),
('Toyota', 'toyota'),
('Honda', 'honda')
ON CONFLICT (name_normalized) DO NOTHING;

INSERT INTO pre_search_brand_alias (brand_id, alias, alias_normalized)
SELECT b.id, vals.alias, vals.alias_normalized
FROM pre_search_brand b
JOIN (
    VALUES
        ('ford', 'Ford', 'ford'),
        ('chevrolet', 'Chevrolet', 'chevrolet'),
        ('chevrolet', 'GM', 'gm'),
        ('volkswagen', 'Volkswagen', 'volkswagen'),
        ('volkswagen', 'VW', 'vw'),
        ('fiat', 'Fiat', 'fiat'),
        ('toyota', 'Toyota', 'toyota'),
        ('honda', 'Honda', 'honda')
) AS vals(brand_norm, alias, alias_normalized)
    ON vals.brand_norm = b.name_normalized
ON CONFLICT (alias_normalized) DO NOTHING;

INSERT INTO pre_search_model (brand_id, name, name_normalized)
SELECT b.id, vals.model_name, vals.model_norm
FROM pre_search_brand b
JOIN (
    VALUES
        ('ford', 'EcoSport', 'ecosport'),
        ('ford', 'Fiesta', 'fiesta'),
        ('ford', 'Focus', 'focus'),
        ('volkswagen', 'Gol', 'gol'),
        ('fiat', 'Palio', 'palio'),
        ('fiat', 'Uno', 'uno'),
        ('chevrolet', 'Onix', 'onix'),
        ('chevrolet', 'S10', 's10'),
        ('toyota', 'Corolla', 'corolla'),
        ('toyota', 'Hilux', 'hilux'),
        ('honda', 'Civic', 'civic')
) AS vals(brand_norm, model_name, model_norm)
    ON vals.brand_norm = b.name_normalized
ON CONFLICT (brand_id, name_normalized) DO NOTHING;

INSERT INTO pre_search_model_alias (model_id, alias, alias_normalized)
SELECT m.id, vals.alias, vals.alias_norm
FROM pre_search_model m
JOIN (
    VALUES
        ('ecosport', 'EcoSport', 'ecosport'),
        ('fiesta', 'Fiesta', 'fiesta'),
        ('focus', 'Focus', 'focus'),
        ('gol', 'Gol', 'gol'),
        ('palio', 'Palio', 'palio'),
        ('uno', 'Uno', 'uno'),
        ('onix', 'Onix', 'onix'),
        ('corolla', 'Corolla', 'corolla'),
        ('corolla', 'Corola', 'corola'),
        ('civic', 'Civic', 'civic'),
        ('s10', 'S10', 's10'),
        ('hilux', 'Hilux', 'hilux')
) AS vals(model_norm, alias, alias_norm)
    ON vals.model_norm = m.name_normalized
ON CONFLICT (alias_normalized) DO NOTHING;

INSERT INTO pre_search_part_type (name, name_normalized, category_name) VALUES
('filtro de oleo', 'filtro de oleo', 'FILTROS'),
('filtro de ar', 'filtro de ar', 'FILTROS'),
('filtro combustivel', 'filtro combustivel', 'FILTROS'),
('filtro', 'filtro', 'FILTROS'),
('bandeja', 'bandeja', 'SUSPENSAO'),
('pastilha de freio', 'pastilha de freio', 'FREIOS'),
('disco de freio', 'disco de freio', 'FREIOS'),
('amortecedor', 'amortecedor', 'SUSPENSAO'),
('coxim motor', 'coxim motor', 'BUCHAS - COXINS - SANFONAS'),
('coxim', 'coxim', 'BUCHAS - COXINS - SANFONAS'),
('bomba combustivel', 'bomba combustivel', 'INJECAO E CARBURACAO'),
('bomba d''agua', 'bomba d''agua', 'ARREFECIMENTO - MOTOR'),
('rolamento roda', 'rolamento roda', 'ROLAMENTOS E CUBOS'),
('farol', 'farol', 'ACESSORIOS E CARROCERIA'),
('correia dentada', 'correia dentada', 'CORREIAS'),
('kit correia', 'kit correia', 'CORREIAS'),
('retrovisor', 'retrovisor', 'ACESSORIOS E CARROCERIA'),
('sensor abs', 'sensor abs', 'ELETRICA E IGNICAO'),
('radiador', 'radiador', 'ARREFECIMENTO - MOTOR'),
('parachoque', 'parachoque', 'ACESSORIOS E CARROCERIA'),
('vela ignicao', 'vela ignicao', 'ELETRICA E IGNICAO'),
('motor arranque', 'motor arranque', 'ELETRICA E IGNICAO'),
('bico injetor', 'bico injetor', 'INJECAO E CARBURACAO'),
('kit embreagem', 'kit embreagem', 'EMBREAGEM E CAMBIO'),
('embreagem', 'embreagem', 'EMBREAGEM E CAMBIO'),
('lanterna traseira', 'lanterna traseira', 'ACESSORIOS E CARROCERIA'),
('correia', 'correia', 'CORREIAS')
ON CONFLICT (name_normalized) DO NOTHING;

INSERT INTO pre_search_part_alias (part_type_id, alias, alias_normalized)
SELECT pt.id, vals.alias, vals.alias_norm
FROM pre_search_part_type pt
JOIN (
    VALUES
        ('filtro de oleo', 'filtro de oleo', 'filtro de oleo'),
        ('filtro de oleo', 'filtro oleo', 'filtro oleo'),
        ('filtro de ar', 'filtro de ar', 'filtro de ar'),
        ('filtro de ar', 'filtro ar', 'filtro ar'),
        ('filtro combustivel', 'filtro de combustivel', 'filtro de combustivel'),
        ('filtro combustivel', 'filtro combustivel', 'filtro combustivel'),
        ('filtro', 'filtro', 'filtro'),
        ('bandeja', 'bandeja', 'bandeja'),
        ('bandeja', 'bandenja', 'bandenja'),
        ('bandeja', 'bandeija', 'bandeija'),
        ('pastilha de freio', 'pastilha de freio', 'pastilha de freio'),
        ('pastilha de freio', 'pastilha freio', 'pastilha freio'),
        ('pastilha de freio', 'pastilha', 'pastilha'),
        ('disco de freio', 'disco de freio', 'disco de freio'),
        ('disco de freio', 'disco freio', 'disco freio'),
        ('amortecedor', 'amortecedor', 'amortecedor'),
        ('coxim motor', 'coxim motor', 'coxim motor'),
        ('coxim', 'coxim', 'coxim'),
        ('bomba combustivel', 'bomba combustivel', 'bomba combustivel'),
        ('bomba combustivel', 'bomba de combustivel', 'bomba de combustivel'),
        ('bomba d''agua', 'bomba dagua', 'bomba dagua'),
        ('bomba d''agua', 'bomba d''agua', 'bomba d''agua'),
        ('bomba d''agua', 'bomba de agua', 'bomba de agua'),
        ('rolamento roda', 'rolamento de roda', 'rolamento de roda'),
        ('rolamento roda', 'rolamento roda', 'rolamento roda'),
        ('farol', 'farol', 'farol'),
        ('correia dentada', 'correia dentada', 'correia dentada'),
        ('kit correia', 'kit correia', 'kit correia'),
        ('retrovisor', 'retrovisor', 'retrovisor'),
        ('sensor abs', 'sensor abs', 'sensor abs'),
        ('radiador', 'radiador', 'radiador'),
        ('parachoque', 'parachoque', 'parachoque'),
        ('parachoque', 'para choque', 'para choque'),
        ('vela ignicao', 'vela ignicao', 'vela ignicao'),
        ('vela ignicao', 'vela de ignicao', 'vela de ignicao'),
        ('vela ignicao', 'velas ignicao', 'velas ignicao'),
        ('motor arranque', 'motor arranque', 'motor arranque'),
        ('motor arranque', 'arranque', 'arranque'),
        ('bico injetor', 'bico injetor', 'bico injetor'),
        ('kit embreagem', 'kit embreagem', 'kit embreagem'),
        ('embreagem', 'embreagem', 'embreagem'),
        ('lanterna traseira', 'lanterna traseira', 'lanterna traseira'),
        ('lanterna traseira', 'lanterna', 'lanterna'),
        ('correia', 'correia', 'correia')
) AS vals(part_norm, alias, alias_norm)
    ON vals.part_norm = pt.name_normalized
ON CONFLICT (alias_normalized) DO NOTHING;

INSERT INTO pre_search_part_rule (part_type_id, is_generic, needs_side, needs_position, needs_engine)
SELECT pt.id, vals.is_generic, vals.needs_side, vals.needs_position, vals.needs_engine
FROM pre_search_part_type pt
JOIN (
    VALUES
        ('filtro', TRUE, FALSE, FALSE, FALSE),
        ('correia', TRUE, FALSE, FALSE, TRUE),
        ('pastilha de freio', TRUE, FALSE, TRUE, FALSE),
        ('bandeja', FALSE, TRUE, FALSE, FALSE),
        ('farol', FALSE, TRUE, FALSE, FALSE),
        ('retrovisor', FALSE, TRUE, FALSE, FALSE),
        ('lanterna traseira', FALSE, TRUE, FALSE, FALSE),
        ('sensor abs', FALSE, TRUE, TRUE, FALSE),
        ('amortecedor', FALSE, TRUE, TRUE, FALSE),
        ('disco de freio', FALSE, FALSE, TRUE, FALSE),
        ('rolamento roda', FALSE, FALSE, TRUE, FALSE),
        ('parachoque', FALSE, FALSE, TRUE, FALSE),
        ('correia dentada', FALSE, FALSE, FALSE, TRUE),
        ('kit correia', FALSE, FALSE, FALSE, TRUE),
        ('bomba d''agua', FALSE, FALSE, FALSE, TRUE),
        ('radiador', FALSE, FALSE, FALSE, TRUE),
        ('vela ignicao', FALSE, FALSE, FALSE, TRUE),
        ('motor arranque', FALSE, FALSE, FALSE, TRUE),
        ('bico injetor', FALSE, FALSE, FALSE, TRUE),
        ('embreagem', FALSE, FALSE, FALSE, TRUE),
        ('kit embreagem', FALSE, FALSE, FALSE, TRUE)
) AS vals(part_norm, is_generic, needs_side, needs_position, needs_engine)
    ON vals.part_norm = pt.name_normalized
ON CONFLICT (part_type_id) DO UPDATE
SET is_generic = EXCLUDED.is_generic,
    needs_side = EXCLUDED.needs_side,
    needs_position = EXCLUDED.needs_position,
    needs_engine = EXCLUDED.needs_engine,
    updated_at = NOW(),
    updated_by = 'seed';

INSERT INTO pre_search_engine_option (model_id, engine_option, sort_order, year_from, year_to)
SELECT m.id, vals.engine_option, vals.sort_order, vals.year_from, vals.year_to
FROM pre_search_model m
JOIN (
    VALUES
        ('ecosport', '1.6', 1, NULL::INTEGER, NULL::INTEGER),
        ('ecosport', '2.0', 2, NULL::INTEGER, NULL::INTEGER),
        ('ecosport', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('gol', '1.0', 1, NULL::INTEGER, NULL::INTEGER),
        ('gol', '1.6', 2, NULL::INTEGER, NULL::INTEGER),
        ('gol', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('fiesta', '1.0', 1, NULL::INTEGER, NULL::INTEGER),
        ('fiesta', '1.6', 2, NULL::INTEGER, NULL::INTEGER),
        ('fiesta', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('onix', '1.0', 1, NULL::INTEGER, NULL::INTEGER),
        ('onix', '1.4', 2, NULL::INTEGER, NULL::INTEGER),
        ('onix', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('civic', '1.8', 1, NULL::INTEGER, NULL::INTEGER),
        ('civic', '2.0', 2, NULL::INTEGER, NULL::INTEGER),
        ('civic', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('corolla', '1.8', 1, NULL::INTEGER, NULL::INTEGER),
        ('corolla', '2.0', 2, NULL::INTEGER, NULL::INTEGER),
        ('corolla', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER),
        ('hilux', '2.5', 1, NULL::INTEGER, NULL::INTEGER),
        ('hilux', '3.0', 2, NULL::INTEGER, NULL::INTEGER),
        ('hilux', 'Nao sei', 3, NULL::INTEGER, NULL::INTEGER)
) AS vals(model_norm, engine_option, sort_order, year_from, year_to)
    ON vals.model_norm = m.name_normalized
ON CONFLICT (model_id, engine_option, sort_order) DO NOTHING;

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

INSERT INTO pre_search_part_code_pattern (brand_id, pattern_regex, description)
VALUES
(NULL, '\y[A-Za-z]{2,5}[- ]?\d{3,8}\y', 'Padrao generico de codigo de peca')
ON CONFLICT DO NOTHING;
