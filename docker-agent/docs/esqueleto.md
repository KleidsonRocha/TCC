# Esqueleto Tecnico - docker-agent (estado atual)

## 1. Escopo atual
- Pre-search com LLM + extracao deterministica.
- Catalogo em Postgres no modelo `dominio + aliases`.
- Sem fallback hardcoded de catalogo.
- Busca de itens ainda mock (`search_parts`).

## 2. Endpoints
- `GET /health`
- `POST /respond`

## 3. Regras-chave
- `schema_version` deve ser `1.0`.
- `message.text` nao pode ser vazio.
- `part_query` ausente e `part_code` ausente -> `ask`.
- `part_code` valido -> `search`.

## 4. Catalogo (DB)
Tabelas principais:
- `pre_search_brand`
- `pre_search_brand_alias`
- `pre_search_model`
- `pre_search_model_alias`
- `pre_search_part_type`
- `pre_search_part_alias`
- `pre_search_part_rule`
- `pre_search_engine_option`
- `pre_search_invalid_slot_token`
- `pre_search_part_code_pattern`

Campos de governanca em todas as tabelas de dominio:
- `is_active`
- `created_at`
- `updated_at`
- `updated_by`

## 5. Slots
`criteria` contempla:
- `part_query`
- `part_code`
- `vehicle_brand`
- `vehicle_model`
- `vehicle_year`
- `engine`
- `side`
- `position`
- `quantity`

## 6. Componentes internos
- `LLMPreSearchValidator`: chamada LLM + coercao + merge com extraido.
- `DictionaryPreSearchExtractor`: extracao por alias/tokens do catalogo.
- `PostgresPreSearchCatalogProvider`: leitura do catalogo.
- `ProcessAgentRequestUseCase`: orquestracao final.

## 7. Falhas esperadas
- DB indisponivel ou schema incompleto: app falha no startup (modo strict).
- LLM indisponivel durante request: HTTP 503 no `/respond`.

