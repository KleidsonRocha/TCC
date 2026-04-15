# Mapa Da Documentacao

Esta pasta foi reorganizada para manter menos arquivos, com foco no que e operacional, atual e util para banca, manutencao e evolucao do projeto.

## Leitura Recomendada

1. `../README.md`
2. `guide/pre_search_runtime_flow.md`
3. `guide/runtime_and_bootstrap.md`
4. `training/pre_search_fine_tuning.md`
5. `DECISIONS.md`
6. `PROGRESS.md`
7. `TODO.md`

## Estrutura Atual

- `guide/`
  - `pre_search_runtime_flow.md`: detalhamento do fluxo funcional do `/respond`
  - `runtime_and_bootstrap.md`: subida da stack, bootstrap e catalogo
  - `operational_commands.md`: comandos de operacao, teste e treino
  - `erp_search_integration.md`: camada de pesquisa no ERP consumida pelo runtime

- `training/`
  - `pre_search_fine_tuning.md`: fluxo de revisao, promocao, exportacao, treino e publicacao

- `DECISIONS.md`
  - registro das escolhas tecnicas e do motivo de cada uma

- `PROGRESS.md`
  - consolidacao do estado atual do projeto, evidencias e proximos blocos

- `TODO.md`
  - backlog priorizado e plano operacional

- `assets/`
  - `datasets/`: datasets oficiais de avaliacao e benchmark
  - `reports/`: relatorios e analises de progresso
  - `sql/`: SQLs auxiliares

## Regras De Organizacao

- documentacao normativa e atual fica no nivel `docs/` ou em `docs/guide/` e `docs/training/`
- artefatos auxiliares ficam em `docs/assets/`
- seeds reais de bootstrap ficam em `db/init/csv/`, nao em `docs/`
- material antigo e fragmentado foi removido para reduzir duplicidade e links quebrados

## Criterio De Uso

- para entender o funcionamento do agente em alto nivel: `../README.md`
- para detalhar o fluxo funcional do runtime: `guide/pre_search_runtime_flow.md`
- para subir ambiente e banco: `guide/runtime_and_bootstrap.md`
- para operar a stack: `guide/operational_commands.md`
- para entender a integracao de busca com o ERP: `guide/erp_search_integration.md`
- para entender treino e revisao: `training/pre_search_fine_tuning.md`
- para justificar escolhas tecnicas: `DECISIONS.md`
- para ver status atual e evidencias: `PROGRESS.md`
- para ver backlog e proximos passos: `TODO.md`
