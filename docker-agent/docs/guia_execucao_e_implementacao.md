# Guia de Execucao e Implementacao - docker-agent

## 1. O que esta implementado
- Validador de pre-busca baseado em LLM.
- Extracao deterministica de slots com catalogo em banco.
- Catalogo de negocio no Postgres (`dominio + aliases`).
- `search_parts` ainda mock (fase atual).

## 2. Pre-requisitos
- Docker Desktop com engine ativo.
- `docker-comm` apontando para `AGENT_URL=http://docker-agent:8001/respond` quando ambos em Docker.

## 3. Subir stack
```powershell
cd d:\TCC\docker-agent
docker compose up -d --build
```

Servicos esperados:
- `docker-agent` em `:8001`
- `ollama` em `:11434`
- `presearch-db` em `:5433`

## 4. Variaveis importantes
- `CATALOG_DB_ENABLED=true`
- `CATALOG_DB_HOST=presearch-db`
- `CATALOG_DB_PORT=5432`
- `CATALOG_DB_NAME=presearch`
- `CATALOG_DB_USER=presearch`
- `CATALOG_DB_PASSWORD=presearch`
- `LLM_BASE_URL=http://ollama:11434`
- `LLM_MODEL=qwen2.5:7b`

## 5. Seed e migracao
Primeiro bootstrap (volume novo):
- `db/init/001_pre_search_catalog.sql` roda automaticamente.

Volume antigo com schema anterior:
- aplicar migracao `db/migrations/002_pre_search_domain_aliases.sql`.

## 6. Checks rapidos
Health:
```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8001/health"
```

Logs de carga de catalogo:
- procurar `pre_search_catalog_db_loaded` no `docker-agent`.

## 7. Fluxo do /respond (resumo)
1. valida contrato.
2. valida pre-search (`decision`, `criteria`, `missing_fields`, `next_question`).
3. `ask` -> retorna pergunta.
4. `search` -> chama `search_parts` mock.
5. monta `handoff`, `confidence`, `tool_trace`.

## 8. Campos de criteria aceitos
- `part_query`, `part_code`, `vehicle_brand`, `vehicle_model`, `vehicle_year`, `engine`, `side`, `position`, `quantity`.

## 9. Observacoes de operacao
- Catalogo esta em modo strict: se DB/schema obrigatorio estiver ausente, startup falha.
- Isso e intencional para manter o banco como fonte unica da verdade.

