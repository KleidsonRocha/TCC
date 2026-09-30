# Datasets de avaliacao

Os arquivos deste diretorio servem a etapas diferentes do ciclo de validacao do agente. Eles podem ser agrupados por finalidade, mas nao devem ser fundidos em um unico conjunto: formato, criterio de sucesso, origem e consumidor variam.

## Inventario por finalidade

### Pre-search e parametros do LLM

- [`pre_search_eval_dataset_mvp.json`](pre_search_eval_dataset_mvp.json) — conjunto curto de 20 pedidos para avaliar a extracao e as perguntas do pre-search.
- [`pre_search_num_predict_golden_set.json`](pre_search_num_predict_golden_set.json) — conjunto de 25 casos usado no benchmark do parametro `num_predict` e na avaliacao golden do pre-search.

Os dois arquivos usam registros de entrada/expectativa semelhantes, mas tem papeis de avaliacao diferentes e consumidores proprios. Devem permanecer separados enquanto o relatorio e o benchmark os selecionarem independentemente.

### Busca SQL do ERP

- [`erp_search_golden_set.json`](erp_search_golden_set.json) — 45 casos e seis grupos de fixtures para identidade da peca, aplicacao do veiculo, filtros e ranking da busca SQL. E consumido pelo avaliador ERP e pelas regressoes PostgreSQL.
- [`erp_manual_type_validation_v1.json`](erp_manual_type_validation_v1.json) — caderno progressivo de oito validacoes manuais, com conversa, consulta ERP, aplicacoes conferidas e divergencias. Esta em andamento e nao e um golden set executavel.

O golden set ERP testa regras e resultados controlados; a validacao manual registra evidencias comerciais reais e itens ainda pendentes. Manter separados evita transformar observacoes parciais em expectativas aprovadas.

### Endpoint de conversa `respond`

- [`battery_structural_respond_v2.json`](battery_structural_respond_v2.json) — 151 cenarios multi-turno com niveis cumulativos `smoke`, `regression` e `extended`, usados em testes estruturais e de integracao.
- [`battery_real_omnichannel_250.json`](battery_real_omnichannel_250.json) — 250 cenarios derivados de conversas reais omnichannel. Expectativas comerciais ou semanticas ficam sujeitas a revisao humana; os cenarios nao aprovados nao devem ser tratados como rotulos golden.

As duas baterias compartilham a ideia de cenario multi-turno, mas diferem na origem e no nivel de aprovacao. A bateria real nao deve ser incorporada automaticamente a estrutural: isso mudaria a confiabilidade dos resultados de CI.

### Ranking real anotado por humanos

- [`real_respond_ranking_annotations_v1.json`](real_respond_ranking_annotations_v1.json) — ficha independente de anotacao manual de compatibilidade ERP por consulta e item. O arquivo inicial tem 143 consultas capturadas na execucao local de 29/09/2026; todos os rótulos estao pendentes e **nao** formam um gabarito ainda.

Cada registro usa `scenario_id`, `turn_id` e `item_index` para identificar uma consulta, inclusive quando uma mensagem gera buscas para varias pecas. Revise a aplicacao no ERP sem usar o ranking da IA para decidir compatibilidade. Preencha todos os codigos tecnicamente compativeis, os codigos preferidos/confirmados pelo vendedor, incompatibilidades comprovadas e grupos de codigos equivalentes. Marque `evaluable: true` somente quando houver evidencia suficiente. Para um no-match confirmado, use `expected_no_match: true` e deixe `compatible_item_ids` vazio.

Gere a ficha uma vez a partir da execucao-base e preencha os rotulos. Para comparar outra execucao, informe o mesmo arquivo de anotacoes nos dois runs:

```powershell
$baseRun = ".tmp/eval/arquivo_base.json"
$currentRun = ".tmp/eval/arquivo_atual.json"
python -m scripts.eval.build_real_ranking_annotation_template --run $baseRun --output docs/assets/datasets/real_respond_ranking_annotations_v1.json
python -m scripts.eval.evaluate_real_ranking --run $currentRun --compare-run $baseRun --annotations docs/assets/datasets/real_respond_ranking_annotations_v1.json --output .tmp/eval/ranking_comparison.md
```

O gerador recusa sobrescrever um arquivo existente. Para adicionar uma coorte nova, escolha outro caminho e depois consolide apenas as anotacoes revisadas. Para uma comparacao pareada, use a mesma ficha e as mesmas chaves nos dois JSONs de execucao. O avaliador mede compatibilidade Top-1/Top-3, preferencia/confirmacao Top-1, candidatos incompativeis no Top-3 e no-match. Empate aceitavel so conta como equivalencia da preferencia quando foi anotado; nao transforma sozinho um codigo em compativel.

O baseline historico de 40,0% Top-1 e 68,8% Top-3 nao tem os 20 rankings originais arquivados por consulta neste repositorio. Sem recuperar esses resultados e suas chaves, a anotacao nova mede uma baseline nova e nao permite afirmar ganho direto sobre aqueles percentuais.

## Convencao de nomes e metadados

Os nomes atuais usam `snake_case` e, em geral, indicam dominio e finalidade. Ainda nao existe uma convencao formal uniforme. Para novos arquivos, usar:

`<dominio>_<finalidade>[_<origem>]_v<major>.json`

Usar metadados no proprio arquivo para descrever versao de schema, quantidade, status de curadoria, origem e consumidores. A versao no nome indica mudanca incompatível do dataset, nao cada edicao de conteudo. Evitar incluir quantidade no nome, pois ela muda com a curadoria.

Pontos atuais a harmonizar em uma migracao futura:

- `battery_structural_respond_v2.json` tem ordem diferente dos outros nomes de bateria e metadado interno `real_respond_battery_v2`; escolher uma forma canonica quando for feita migracao de caminhos.
- `battery_real_omnichannel_250.json` embute a quantidade no nome e usa ordem diferente do campo interno `real_omnichannel_battery_250`.
- Os dois arquivos `pre_search_*.json` sao arrays sem envelope de metadados, enquanto as baterias e o dataset manual tem objeto raiz com nome/versao/status.
- `erp_search_golden_set.json` usa `contract_version` e nao tem `name` nem `schema_version`, diferente dos outros objetos-raiz.

Os caminhos existentes estao referenciados por scripts, testes e documentacao; manter os nomes atuais ate uma migracao coordenada atualizar esses consumidores.

## Curadoria e promocao

1. Casos coletados ou gerados entram como candidatos e recebem origem e contexto.
2. Casos manuais precisam de revisao da aplicacao no ERP e do resultado esperado.
3. Somente casos aprovados viram expectativas golden ou regressao automatizada.
4. Incidentes de infraestrutura, como timeout, ficam registrados separados da qualidade de cobertura.

A bateria omnichannel pode conter casos marcados `review_required`; eles servem para exploracao e revisao, nao como verdade comercial aprovada. O caderno ERP fica fora do treinamento ate a revisao humana estar concluida.

## Comandos e consumidores

Consulte [`scripts/README.md`](../../../scripts/README.md), [`operational_commands.md`](../../guide/operational_commands.md) e [`erp_search_integration.md`](../../guide/erp_search_integration.md) para executar os avaliadores. A lista de alteracoes pendentes de validacao manual fica em [`docs/TODO.md`](../../TODO.md).
