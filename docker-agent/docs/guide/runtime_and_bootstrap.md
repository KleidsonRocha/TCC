# Runtime And Bootstrap

## Runtime

O runtime da API esta em:
- `app/`
- `docker-compose.yml`
- `.env`

Isso cobre:
- subida do `docker-agent`
- integracao com `ollama`
- leitura do catalogo no Postgres
- fluxo `/respond`

## Bootstrap do catalogo deterministico

O bootstrap do banco esta em:
- `db/init/pre_search_init.sql`
- `db/init/csv/`
- `scripts/db/import_pre_search_catalog_csv.py`

Uso pratico:
- `db/init/csv/` = dados que o Postgres pode consumir no nascimento da base
- `docs/assets/db_bootstrap_csv/` = templates e exemplos de formato

## Fine-tuning

O fluxo de dataset e treino esta em:
- `db/init/pre_search_init.sql`
- `scripts/training/`
- `trainer/`

Guia principal:
- `../training/pre_search_fine_tuning.md`

## Comandos operacionais

Guia rapido de comandos:
- `operational_commands.md`
