# Docs Map

## O que fica aqui

- `guide/operational_commands.md`
  Comandos operacionais do dia a dia: stack, banco, testes, revisao, avaliacao e fine-tuning.
- `guide/runtime_and_bootstrap.md`
  Mapa curto do runtime, bootstrap do banco e fluxo de treino.
- `guide/erp_item_search_candidates_view.md`
  Proposta de view no ERP para busca real de candidatos de pecas.
- `TODO.md`
  Roadmap operacional do projeto.
- `training/pre_search_fine_tuning.md`
  Guia vivo do fluxo de fine-tuning, revisao e promocao de modelo.
- `assets/datasets/`
  Datasets usados por avaliacao e benchmark.
- `assets/sql/`
  SQLs auxiliares que servem como proposta de integracao e artefatos de apoio.
- `assets/llm/`
  Insumos auxiliares de prompt/catalogo para a LLM.
- `assets/db_bootstrap_csv/`
  Templates de CSV do catalogo deterministico. Servem para referencia de formato.
- `archive/`
  Documentacao historica. Nao deve ser tratada como fonte principal de operacao.

## Regra de organizacao

- documento operacional atual: fica em `docs/` ou `docs/training/`
- dataset ou arquivo auxiliar: fica em `docs/assets/`
- material antigo, duplicado ou historico: vai para `docs/archive/`

## Ordem de leitura

1. `../README.md`
2. `guide/operational_commands.md`
3. `guide/runtime_and_bootstrap.md`
4. `training/pre_search_fine_tuning.md`
5. `TODO.md`
