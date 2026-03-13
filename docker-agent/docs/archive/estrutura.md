# docker-agent - Estrutura Atual (catalogo em banco)

## 1. Objetivo
O `docker-agent` recebe mensagens do `docker-comm` em `POST /respond`, valida pre-busca com LLM + extracao deterministica, aplica regras de decisao e retorna resposta estruturada.

## 2. Arquitetura atual
- API: FastAPI (`/health`, `/respond`)
- Orquestracao: `ProcessAgentRequestUseCase`
- Validador: `LLMPreSearchValidator`
- Extrator deterministico: `DictionaryPreSearchExtractor`
- Busca: `search_parts` (mock)
- Catalogo de dominio: Postgres `presearch-db` (strict mode)

## 3. Catalogo pre-search (fonte unica)
Modelo `dominio + aliases`:
- `pre_search_brand` + `pre_search_brand_alias`
- `pre_search_model` + `pre_search_model_alias`
- `pre_search_part_group`
- `pre_search_part_type` + `pre_search_part_alias`
- `pre_search_part_rule`
- `pre_search_engine_option`
- `pre_search_invalid_slot_token`
- `pre_search_part_code_pattern`

Seed inicial:
- `db/init/001_pre_search_catalog.sql`
- se os CSVs estiverem em `db/init/csv/`, o proprio `001` faz bootstrap completo no nascimento da base

Sem migrations: em mudanca de schema, recriar volume do Postgres para reaplicar o `init`.

## 4. Modo strict de catalogo
- `CATALOG_DB_ENABLED=true` e obrigatorio.
- Sem fallback hardcoded em memoria para catalogo de negocio.
- Se o schema/tabelas obrigatorias nao existirem, o app falha no startup (fail fast).

## 5. Slots suportados no pre-search
- `part_query`
- `part_code`
- `vehicle_brand`
- `vehicle_model`
- `vehicle_year`
- `engine`
- `side`
- `position`
- `axle`
- `variant`
- `quantity`

## 6. Regras de decisao
- `schema_version != 1.0` -> HTTP 400
- `message.text` vazio -> HTTP 400
- Sem `part_query` e sem `part_code` -> `ask`
- Com `part_code` valido -> `search`
- Ambiguos (`filtro`, `correia`, `pastilha de freio`) sem contexto suficiente -> `ask`
- `search_parts` sem resultados -> `handoff.required=true`

## 7. Estrutura de pastas
```text
docker-agent/
  app/
    main.py
    api/
    core/
      domain/
        pre_search.py
        pre_search_catalog.py
      usecases/
        process_agent_request.py
    infra/
      pre_search_validator_llm.py
      pre_search_dictionary_extractor.py
      pre_search_catalog_pg.py
      tools_mock.py
  db/
    init/
      001_pre_search_catalog.sql
      csv/
  scripts/
    import_pre_search_catalog_csv.py
  docs/
  tests/
  docker-compose.yml
  Dockerfile
```
