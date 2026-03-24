# Mapa Da Documentacao

Este diretorio concentra a documentacao normativa e os artefatos auxiliares do projeto.

## Leitura Recomendada

### Para banca e orientacao

1. `../README.md`
2. `guide/repository_reading_path.md`
3. `guide/pre_search_runtime_flow.md`
4. `guide/problem_solution_catalog.md`
5. `guide/runtime_and_bootstrap.md`
6. `TODO.md`

### Para operacao

1. `guide/operational_commands.md`
2. `guide/runtime_and_bootstrap.md`
3. `training/pre_search_fine_tuning.md`

## O Que Cada Area Contem

- `guide/`
  Guias normativos do runtime, da leitura do repositorio e da operacao.
- `training/`
  Fluxo de revisao, exportacao de dataset, benchmark e promocao de modelo.
- `assets/datasets/`
  Datasets usados em avaliacao e benchmark.
- `assets/db_bootstrap_csv/`
  Templates de CSV para referencia de formato.
- `assets/sql/`
  SQLs auxiliares e propostas de integracao.
- `archive/`
  Material historico. Nao e a fonte principal para leitura inicial.

## Regra De Organizacao

- documento atual e normativo: fica em `docs/guide/` ou `docs/training/`
- dataset, exemplo e artefato auxiliar: fica em `docs/assets/`
- material antigo, duplicado ou apenas historico: vai para `docs/archive/`

## Criterio De Uso

- se voce quer entender o funcionamento do agente: comece por `guide/pre_search_runtime_flow.md`
- se voce quer ver o mapa de problemas e solucoes adotados: va para `guide/problem_solution_catalog.md`
- se voce quer reproduzir ambiente e banco: va para `guide/runtime_and_bootstrap.md`
- se voce quer operar a stack: va para `guide/operational_commands.md`
- se voce quer entender treino e revisao: va para `training/pre_search_fine_tuning.md`
