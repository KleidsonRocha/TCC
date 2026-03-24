# Runtime E Bootstrap

## Objetivo

Este guia resume como o ambiente sobe, como o catalogo deterministico nasce no Postgres e quais arquivos formam o runtime minimo do projeto.

## Runtime

Os arquivos centrais de execucao estao em:

- `app/`
- `docker-compose.yml`
- `.env`

Isso cobre:
- subida do `docker-agent`
- integracao com `ollama`
- leitura do catalogo no Postgres
- fluxo `/respond`
- decisao entre `ask`, `search` e `handoff`

## Bootstrap Do Catalogo

A fonte operacional do schema e:

- `db/init/pre_search_init.sql`

Os dados de bootstrap ficam em:

- `db/init/csv/`

Uso pratico:
- `db/init/csv/` contem os seeds reais consumidos pelo banco
- `pre_search_part_alias.csv` concentra cobertura lexical curada
- `docs/assets/db_bootstrap_csv/` guarda apenas templates e exemplos de formato
- qualquer mudanca estrutural de catalogo deve ser refletida no SQL consolidado e nos CSVs de bootstrap
- para reaplicar o catalogo, o fluxo padrao do projeto e recriar o volume do Postgres

## Fine-Tuning

O fluxo de dataset e treino vive em:

- `scripts/training/`
- `trainer/`
- `docs/training/pre_search_fine_tuning.md`

## Comandos

Para operacao do dia a dia:

- `operational_commands.md`

## Fluxo Funcional

Para entender o caminho de texto livre ate pergunta ou pesquisa:

- `pre_search_runtime_flow.md`
