# Datasets De Avaliacao

Esta pasta concentra os datasets usados para avaliar, comparar e expandir o comportamento do pre-search.

## Papel De Cada Arquivo

- `pre_search_eval_dataset_mvp.json`
  Conjunto pequeno e rapido para avaliacao funcional direta.
- `pre_search_num_predict_golden_set.json`
- `erp_search_golden_set.json`: 38 pedidos automotivos e fixtures de identidade/aplicacao,
  consumidos por `scripts.eval.evaluate_erp_search` e pelas regressoes PostgreSQL
  Golden set usado em benchmark e promocao de modelo.
- `battery_structural_respond_v2.json`
  Bateria estrutural multi-turno do endpoint, com niveis cumulativos `smoke`, `regression` e `extended`.
- `battery_real_omnichannel_250.json`
  Bateria de conversas reais omnichannel, com 250 cenarios selecionados.
- `real_respond_battery_human_validation.md`
  Checklist dos casos cujo resultado comercial, discriminador ou politica ainda precisa de aprovacao humana.

## Estrategia Recomendada

### Fase 1

- `MVP`: `80-150` casos
- foco em smoke test, regressao rapida e revisao manual curta

### Fase 2

- `golden set`: `200-400` casos
- foco em promocao de modelo, benchmark e comparacao mais estavel

### Fase 3

- corpus maior: `1000+` casos
- foco em mineracao de falhas, long tail e analise offline
- nao precisa ser o conjunto padrao de benchmark de toda execucao

## De Onde Tirar Casos

Prioridade recomendada:

1. logs e fila de revisao do proprio sistema
2. casos manuais de alta ambiguidade do negocio
3. fontes publicas para ampliar vocabulario e formulacoes

Importante:
- internet deve complementar, nao substituir, os casos reais do seu fluxo
- casos auto-gerados entram como rascunho e exigem revisao antes de virar gold

## Links Publicos Para Pesquisa

- OpenAI eval best practices:
  https://developers.openai.com/api/docs/guides/evaluation-best-practices
- Dynabench:
  https://nlp.cs.ucl.ac.uk/publications/2021-04-dynabench/
- GDPval:
  https://cdn.openai.com/pdf/d5eb7428-c4e9-4a33-bd86-86dd4bcf12ce/GDPval.pdf?_bhlid=032d03cdc21c768f9824f9841b613c0b57764ca3

## Automacao E Curadoria

No estado atual do repositorio, os datasets oficiais ficam curados e versionados:

- `pre_search_eval_dataset_mvp.json`
- `pre_search_num_predict_golden_set.json`
- `battery_structural_respond_v2.json`
- `battery_real_omnichannel_250.json`

A geracao automatica de candidatos foi retirada do fluxo versionado por dois motivos:

- os rascunhos ainda exigiam revisao semantica forte antes de virar benchmark oficial
- o objetivo do repositorio e manter apenas os datasets realmente usados na avaliacao atual

Se a expansao automatica voltar no futuro, a recomendacao e:

- gerar candidatos fora do versionamento
- revisar manualmente os casos promovidos
- versionar apenas o que entrar de fato no MVP ou no golden set

A bateria omnichannel real e uma excecao controlada: os cenarios dependentes do negocio ficam explicitamente marcados com `review_required`. O gerador estrutural nao inventa a resposta comercial nem promove esses casos ao golden set.
