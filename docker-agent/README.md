# docker-agent

Servico FastAPI do TCC para atendimento inicial de autopecas. O projeto recebe texto livre em `POST /respond`, extrai criterios estruturados de busca, decide entre `ask`, `search` e `handoff`, e consulta o ERP apenas quando o criterio estiver suficientemente valido.

## Escopo Atual

- API HTTP no contrato `v1.0`
- catalogo deterministico em Postgres
- extracao lexical com aliases e fuzzy conservador para `part_query`
- bypass deterministico seguro para pedidos completos, follow-ups simples e perguntas obvias
- desambiguacao deterministica e multi-turno quando o ERP retorna varios itens
- validacao com LLM via Ollama
- busca real no ERP via PostgreSQL
- captura de interacoes para revisao e fine-tuning
- API administrativa para revisar visualmente as conversas capturadas
- curadoria multi-item e reabertura auditada de revisoes

## Fluxo Funcional Resumido

O caminho principal do runtime e este:

1. a API recebe texto livre em `POST /respond`
2. o extractor deterministico tenta preencher criterios como `part_query`, `vehicle_model`, `vehicle_year` e `engine`
3. se alias exato, catalogo, regras e score comprovarem que o pedido esta completo, o backend libera `search` sem chamar a LLM
4. se o pedido estiver incompleto, mas a familia e a proxima pergunta forem comprovadas pelas regras, o backend retorna `ask` sem chamar a LLM
5. nos demais casos, o backend monta `dictionary_seed_criteria` e `score_policy`
6. a LLM valida o contexto e sugere `ask`, `search` ou `handoff`
7. o backend recalcula os campos obrigatorios e decide se `search` pode ser liberado
8. so depois disso o sistema consulta `soccol.item_search_candidates` e `soccol.item_search_applications`, validando familia e todos os criterios na mesma aplicacao antes do ranking
9. quando houver varios itens, o backend escolhe um discriminador real, pergunta ao usuario e conserva os candidatos no `ConversationState` persistido pelo Redis

Resumo das decisoes:
- `ask`: quando ainda faltam discriminadores obrigatorios
- `search`: quando o criterio esta suficiente e coerente
- `handoff`: quando o caso foge do escopo ou a busca nao consegue seguir de forma segura

Detalhamento:
- `docs/guide/pre_search_runtime_flow.md`

## Leitura Recomendada

1. `docs/README.md`
2. `docs/guide/pre_search_runtime_flow.md`
3. `docs/guide/runtime_and_bootstrap.md`
4. `docs/training/pre_search_fine_tuning.md`
5. `docs/DECISIONS.md`
6. `docs/PROGRESS.md`
7. `docs/TODO.md`

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

Endpoints administrativos de revisao:
- `GET /review/conversations`: lista conversas pendentes ou concluidas
- `GET /review/conversations/{conversation_id}`: carrega a conversa completa
- `PUT /review/interactions/{id}`: salva a avaliacao de um turno pendente
- `POST /review/interactions/{id}/discard`: descarta um turno inadequado para curadoria
- `POST /review/conversations/{conversation_id}/discard-pending`: descarta todos os turnos ainda pendentes
- `POST /review/interactions/{id}/reopen`: reabre uma revisao ainda nao promovida e preserva seu historico

Esses endpoints podem ser protegidos com `REVIEW_API_KEY`. A interface Streamlit
envia o valor no header `X-Review-Key` e nao acessa o Postgres diretamente.

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

Mutation testing curado:

```bash
python scripts/testing/run_mutation_tests.py --list
python scripts/testing/run_mutation_tests.py review_queue --clean --results
```

Observacao:
- `mutmut` exige suporte a `fork`
- em Windows, rode isso dentro do container `docker-agent` ou via WSL

Artefatos relevantes para avaliacao:
- `docs/assets/datasets/pre_search_eval_dataset_mvp.json`
- `docs/assets/datasets/pre_search_num_predict_golden_set.json`
- `docs/assets/datasets/erp_search_golden_set.json`
- `docs/assets/datasets/battery_structural_respond_v2.json`
- `docs/assets/datasets/battery_real_omnichannel_250.json`
- `docs/assets/datasets/real_respond_battery_human_validation.md`

A bateria real versionada cobre contratos, regras deterministicas, buscas, proveniencia de codigo e conversas multi-turno. Ela pode ser filtrada por `smoke`, `regression` ou `extended`; consulte `docs/guide/operational_commands.md` antes de executar.

## Documentacao Principal

- `docs/README.md`
- `docs/guide/pre_search_runtime_flow.md`
- `docs/guide/erp_search_integration.md`
- `docs/guide/runtime_and_bootstrap.md`
- `docs/guide/operational_commands.md`
- `docs/training/pre_search_fine_tuning.md`
- `docs/DECISIONS.md`
- `docs/PROGRESS.md`
- `docs/HISTORICO.md`
- `docs/TODO.md`

## Higiene Do Repositorio

Arquivos gerados localmente nao fazem parte da entrega:

- `__pycache__/`
- `.pytest_cache/`
- `.tmp/`
- `.env`

Relatorios sao gerados em `.tmp/eval/`; os resultados historicos foram
consolidados em [HISTORICO.md](docs/HISTORICO.md). O DDL operacional do ERP
fica fora do Git. O bootstrap local esta em `db/init/pre_search_init.sql`.
Os dois CSVs gzip do fallback v2 ficam no Git LFS; manifestos e SHA-256
permanecem versionados no Git comum. Execute `git lfs pull` antes de iniciar
um banco novo. Detalhes em [operacao](docs/guide/operational_commands.md#busca-erp-v2-e-snapshot-local).
