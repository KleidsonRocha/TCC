# Progresso Do Projeto

Este documento consolida o estado atual do projeto sem depender de leitura fragmentada de relatorios e arquivos historicos.

## O Que Ja Esta Implementado

- API `POST /respond` e `GET /health`
- extracao deterministica com catalogo em Postgres
- validacao com LLM via Ollama
- gate backend para decidir entre `ask`, `search` e `handoff`
- busca real no ERP
- captura de interacoes reais para revisao
- dataset curado para fine-tuning
- pipeline de exportacao, treino e publicacao de adapter

## O Que Ja Esta Organizado No Banco

- catalogo deterministico e regras no bootstrap consolidado
- fila de revisao em `pre_search_review_interaction`
- dataset formal de treino em:
  - `pre_search_fine_tuning_dataset_header`
  - `pre_search_fine_tuning_dataset_record`
- historico de runs em `pre_search_fine_tuning_run`

## Evidencias Atuais

- testes automatizados em `tests/`
- datasets de avaliacao em `docs/assets/datasets/`
- relatorios de analise em `docs/assets/reports/`

Artefatos de referencia atuais:

- `docs/assets/reports/real_respond_battery_2026-03-25.md`
- `docs/assets/reports/product_owner_analysis_real_battery_2026-03-26.md`
- `docs/assets/reports/pre_search_review_interaction_first_pass_2026-04-15.md`
- `docs/assets/reports/base_model_comparison_2026-04-17.md`

## Comparativo De Modelos Base Antes Do Fine-Tuning

Ja foi executada uma comparacao entre modelos base de runtime antes do primeiro fine-tuning:

- `qwen2.5:7b`
- `qwen3:8b`
- `llama3.1:8b`
- tentativa de `gemma3:12b`, interrompida por inviabilidade operacional

Leitura consolidada:

- `qwen3:8b` apareceu como melhor candidato de equilibrio entre qualidade e latencia
- `qwen2.5:7b` permaneceu como baseline mais seguro
- `llama3.1:8b` foi mais rapido, mas perdeu qualidade no golden set
- `gemma3:12b` nao fechou a bateria real em tempo operacional aceitavel

Esse comparativo foi registrado para deixar explicito que a escolha do modelo base nao ficou restrita a um unico candidato antes da etapa de fine-tuning.

## Estado Atual Do Fine-Tuning

- o fluxo de revisao e promocao ja existe
- o dataset supervisionado ja pode ser exportado para `JSONL`
- o trainer ja esta preparado para `LoRA/QLoRA`
- a etapa mais sensivel para reproducao continua sendo:
  - estado do banco com dados dinamicos
  - disponibilidade de GPU compativel para treino

## Maiores Pendencias Atuais

As pendencias mais importantes continuam no backlog em `TODO.md`, principalmente:

- canonizacao de `part_query`
- bloqueio de `part_code` inventado
- correcao de regras de catalogo que geram perguntas sem sentido
- consolidacao de regressao automatizada para casos reais

## Proxima Fase Recomendada

1. Fechar `Prioridade 0`
2. Reexecutar bateria real e transformar falhas em teste
3. Revisar e promover novas interacoes reais
4. Executar o primeiro ciclo de fine-tuning em maquina com GPU adequada
5. Benchmarkar baseline vs candidato e decidir promocao

## Como Manter Este Documento Util

Atualize este arquivo quando houver:

- mudanca relevante de arquitetura
- novo bloco concluido do backlog
- novo artefato importante de avaliacao
- validacao de reproducao em outro ambiente
