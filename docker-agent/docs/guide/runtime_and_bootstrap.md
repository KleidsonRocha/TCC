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
- `vehicle_model_brand.csv` e a fonte curada da relacao modelo→montadora; o
  bootstrap liga cada registro correspondente em `pre_search_model.brand_id`
  ao registro de `pre_search_brand`
- qualquer mudanca estrutural de catalogo deve ser refletida no SQL consolidado e nos CSVs de bootstrap
- para reaplicar o catalogo, o fluxo padrao do projeto e recriar o volume do Postgres

O vinculo modelo→montadora faz parte do proprio `pre_search_init.sql`; nao
existe SQL auxiliar nem dependencia de ordem entre arquivos. Reiniciar o
container com o mesmo volume nao recria nem perde o catalogo. Para reaplicar
todo o catalogo em um volume ja existente, execute o SQL consolidado dentro do
container Postgres depois de atualizar o checkout:

```bash
docker compose exec -T --user postgres presearch-db sh -c \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/pre_search_init.sql'
```

Antes de ampliar o seed, gere a fila de revisao sem atribuir marcas por
heuristica:

```bash
python -m scripts.catalog.generate_model_brand_review
```

O resultado fica em `.tmp/catalog/model_brand_review.csv`, ordenado pela
recorrencia do modelo em `engine_option.csv`. Revise a montadora e promova
somente registros confirmados para `vehicle_model_brand.csv`.

Se a fila preenchida usar IDs do `pre_search_brand` local, exporte-os e importe
a revisao pelo utilitario. O seed final recebe nomes de montadora, portanto
continua portavel entre bancos:

```bash
docker exec presearch-db psql -U presearch -d presearch -At -F ',' \
  -c 'SELECT id, name FROM pre_search_brand ORDER BY id' \
  > .tmp/catalog/pre_search_brand_ids.csv
python -m scripts.catalog.import_model_brand_review \
  --review .tmp/catalog/model_brand_review_preenchido.csv \
  --brand-ids .tmp/catalog/pre_search_brand_ids.csv \
  --apply
```

## Bootstrap Da Busca Local

O fallback ERP usa o contrato v2 em `soccol.item_search_candidates` e
`soccol.item_search_applications`. O bloco `ERP FALLBACK V2` de
`db/init/pre_search_init.sql` carrega os dois CSVs
comprimidos de `db/init/fallback/v2/`, valida seus checksums e mantem uma chave
estrangeira entre aplicacao e item. O snapshot deve estar presente antes de
inicializar um volume novo. O antigo CSV agregado nao e aceito pelo runtime v2.

Para atualizar somente a busca em volume existente, use
`python -m scripts.erp.install_search_snapshot --apply` no container. O
instalador valida em schema separado e preserva as tabelas anteriores em um
schema de backup; nao e preciso recriar o volume nem perder a fila de revisao.
Sem `--apply`, a validacao termina com rollback.

O DDL do ERP externo e administrado no banco quente, fora do Git deste projeto.
Consulte [integracao ERP](erp_search_integration.md) e
[comandos de operacao](operational_commands.md#busca-erp-v2-e-snapshot-local).

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
