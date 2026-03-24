# docker-agent

Servico FastAPI do TCC para atendimento inicial de autopecas. O projeto recebe texto livre em `POST /respond`, extrai criterios estruturados de busca, decide entre `ask`, `search` e `handoff`, e consulta o ERP apenas quando o criterio estiver suficientemente valido.

## Escopo Atual

- API HTTP no contrato `v1.0`
- catalogo deterministico em Postgres
- extracao lexical com aliases e fuzzy conservador para `part_query`
- validacao com LLM via Ollama
- busca real no ERP via PostgreSQL
- captura de interacoes para revisao e fine-tuning

## Leitura Recomendada

1. `docs/guide/repository_reading_path.md`
2. `docs/guide/pre_search_runtime_flow.md`
3. `docs/guide/problem_solution_catalog.md`
4. `docs/guide/runtime_and_bootstrap.md`
5. `docs/TODO.md`

Esse caminho deixa a leitura mais adequada para orientacao, banca e auditoria tecnica.

## Estrutura Do Repositorio

```text
docker-agent/
  app/        runtime da API e regras de negocio
  db/         schema consolidado e CSVs de bootstrap
  docs/       documentacao normativa, datasets e historico
  scripts/    avaliacao, benchmark e treino
  tests/      testes automatizados
  trainer/    ambiente separado para treino
```

Mapa rapido:
- `app/`
  API, dominio, use cases e integracoes.
- `db/`
  Estrutura e seeds do catalogo deterministico.
- `docs/`
  Material principal de leitura do projeto.
- `scripts/`
  Operacao, benchmark, avaliacao e fine-tuning.
- `tests/`
  Evidencia automatizada de comportamento.
- `trainer/`
  Infra separada para treino, fora do runtime minimo.

## Reproducao Minima

### Requisitos

- Docker e Docker Compose
- opcionalmente Python 3.11+ para execucao local

### Subida da stack

1. copie `.env.example` para `.env`
2. ajuste as variaveis necessarias
3. execute:

```bash
docker compose up --build
```

Servicos principais:
- API: `http://localhost:8001`
- catalogo Postgres: `localhost:5433`
- Ollama: `http://localhost:11434`

## Banco E Bootstrap

O projeto trabalha sem migrations. A fonte operacional do schema e:

- `db/init/pre_search_init.sql`

Os CSVs reais de bootstrap ficam em:

- `db/init/csv/grupo.csv`
- `db/init/csv/subgrupo.csv`
- `db/init/csv/pre_search_part_alias.csv`
- `db/init/csv/pre_search_part_rule.csv`
- `db/init/csv/vehicle_brand.csv`
- `db/init/csv/vehicle_model.csv`
- `db/init/csv/engine_option.csv`

Para recriar a base do zero:

```bash
docker compose down -v
docker compose up -d --build
```

Detalhes adicionais:
- `docs/guide/runtime_and_bootstrap.md`
- `docs/guide/operational_commands.md`

## Validacao

Rodar a suite:

```bash
pytest -q
```

Artefatos relevantes para avaliacao:
- `docs/assets/datasets/pre_search_eval_dataset_mvp.json`
- `docs/assets/datasets/pre_search_num_predict_golden_set.json`

## Documentacao Principal

- `docs/README.md`
- `docs/guide/repository_reading_path.md`
- `docs/guide/pre_search_runtime_flow.md`
- `docs/guide/problem_solution_catalog.md`
- `docs/guide/runtime_and_bootstrap.md`
- `docs/guide/operational_commands.md`
- `docs/training/pre_search_fine_tuning.md`
- `docs/TODO.md`

## Higiene Do Repositorio

Arquivos gerados localmente nao fazem parte da entrega:

- `__pycache__/`
- `.pytest_cache/`
- `.tmp/`
- `.env`
