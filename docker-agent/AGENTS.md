# AGENTS - Regras De Trabalho No Projeto

Este arquivo define o comportamento esperado de qualquer agent que va analisar, editar, testar ou evoluir este repositorio.

O objetivo e preservar consistencia tecnica, evitar retrabalho e impedir que mudancas locais quebrem a coerencia entre runtime, banco, ERP, fine-tuning e documentacao.

## 1. Leitura Obrigatoria Antes De Qualquer Mudanca

Antes de propor ou aplicar qualquer alteracao, leia nesta ordem:

1. `README.md`
2. `docs/README.md`
3. `docs/DECISIONS.md`
4. `docs/PROGRESS.md`
5. `docs/TODO.md`
6. `docs/guide/runtime_and_bootstrap.md`
7. `docs/guide/pre_search_runtime_flow.md`
8. `docs/guide/erp_search_integration.md`
9. `docs/training/pre_search_fine_tuning.md`

Se a mudanca tocar banco, ERP, captacao de revisao ou fine-tuning, essa leitura nao e opcional.

## 2. Regra Central De Arquitetura

Este projeto segue a separacao abaixo:

- banco e catalogo = fonte de verdade estrutural
- backend = regras deterministicas, gate de `search` e coercao defensiva
- LLM = validacao contextual e conducao conversacional
- fine-tuning = especializacao posterior, nao correcao primaria de falha estrutural

Regra principal:

- nao usar ML para mascarar erro de regra, catalogo, bootstrap, ranking ou orquestracao

Antes de propor nova camada de modelo, verifique se a causa raiz nao deveria ser resolvida em:

- `db/init/pre_search_init.sql`
- catalogo bootstrapado
- extractor deterministico
- gate backend
- integracao ERP
- testes de regressao

## 3. Prioridade Tecnica Antes De Evolucao De ML

Qualquer agent deve respeitar a ordem de prioridade do projeto.

Especialmente:

- `Prioridade 0` do `docs/TODO.md` vem antes de novas camadas auxiliares de ML
- fine-tuning nao e a primeira resposta para erro de catalogo
- classificador auxiliar em portugues, como `BERTimbau`, e hipotese futura, nao prioridade atual

## 4. Checklist Antes De Editar

Antes de editar, identificar se a mudanca afeta:

- runtime da API
- bootstrap/schema
- integracao ERP
- fila de revisao
- dataset de fine-tuning
- trainer/publicacao de modelo
- documentacao
- testes

Tambem verificar impacto nos arquivos centrais:

- `app/main.py`
- `app/core/usecases/process_agent_request.py`
- `app/infra/pre_search_validator_llm.py`
- `app/infra/pre_search_catalog_pg.py`
- `app/infra/erp_search_tools_pg.py`
- `app/infra/pre_search_review_queue_pg.py`
- `db/init/pre_search_init.sql`
- `scripts/training/review_pre_search_queue.py`
- `scripts/training/export_pre_search_fine_tuning_dataset.py`
- `scripts/training/run_pre_search_fine_tuning_cycle.py`
- `tests/`

## 5. Regras De Consistencia De Dados E Banco

- `db/init/pre_search_init.sql` e a fonte consolidada de schema e bootstrap do banco local do projeto
- os CSVs reais de bootstrap ficam em `db/init/csv/`
- nao criar seeds paralelos em `docs/`
- se mudar nome de tabela, coluna, view ou contrato de exportacao, atualizar:
  - SQL consolidado
  - scripts Python afetados
  - documentacao

Separacao obrigatoria:

- `pre_search_review_interaction` = fila bruta de interacoes reais para revisao
- `pre_search_fine_tuning_dataset_header` = cabecalho/versionamento do dataset
- `pre_search_fine_tuning_dataset_record` = registros curados do dataset de treino
- `pre_search_fine_tuning_run` = historico de runs

Nao misturar fila operacional com dataset formal de treino.

## 6. Regras De Integracao Com O ERP

O runtime consulta:

- `soccol.item_search_candidates`

Esse objeto pertence ao banco ERP e nao ao banco local de catalogo.

O modulo documental correspondente e:

- `docs/assets/sql/erp_search_integration_candidates_runtime.sql`
- `docs/guide/erp_search_integration.md`

Se houver mudanca em busca ERP:

- validar compatibilidade com `app/infra/erp_search_tools_pg.py`
- nao mover SQL de integracao ERP para `db/init/`
- manter claro que isso e uma camada externa de integracao

## 7. Regras De Fine-Tuning

O fluxo correto e:

1. capturar interacoes reais
2. revisar
3. promover
4. exportar
5. treinar
6. benchmarkar
7. publicar/promover modelo

Regras obrigatorias:

- nao treinar direto de `pre_search_review_interaction`
- somente exemplos revisados e promovidos entram no dataset formal
- manter separacao entre runtime e trainer
- tratar `LoRA/QLoRA` como estrategia padrao do projeto ate decisao metodologica explicita em contrario

Motivo:

- o projeto usa dataset supervisionado estruturado
- o fine-tuning existe para especializacao de dominio com custo viavel
- o objetivo nao e full fine-tuning do backbone

## 8. Regras Para Documentacao

Uso correto dos documentos:

- `README.md` = visao geral do projeto e fluxo resumido
- `docs/README.md` = mapa da documentacao
- `docs/guide/` = detalhes de runtime, bootstrap, ERP e operacao
- `docs/training/` = revisao, dataset, treino, benchmark e publicacao
- `docs/DECISIONS.md` = motivo das escolhas tecnicas
- `docs/PROGRESS.md` = estado atual e evidencias
- `docs/TODO.md` = backlog e plano operacional
- `docs/assets/` = artefatos auxiliares, datasets, relatorios e SQLs documentais

Regras:

- nao criar documento novo se o tema couber claramente em um documento existente
- nao deixar documento duplicado dizendo a mesma coisa com nomes diferentes
- se remover ou renomear um arquivo, atualizar referencias
- evitar misturar portugues e ingles no mesmo documento, salvo nomes tecnicos inevitaveis

## 9. Regras Para Testes

Toda correcao relevante de regra deve virar regressao automatizada quando fizer sentido.

Priorizar cobertura em:

- `tests/test_rules.py`
- `tests/test_process_agent_request_review_capture.py`
- testes de fluxo da API
- testes do ciclo de treino quando a mudanca tocar exportacao, promocao ou publicacao

Se a mudanca nao puder ser testada imediatamente:

- explicitar a lacuna
- registrar qual teste deveria existir

## 10. Regras Para Alteracoes Estruturais

Se uma mudanca mexer em:

- naming de tabela/view
- contratos entre modulos
- bootstrap do banco
- objetos esperados no ERP
- fluxo de revisao/promocao
- localizacao dos arquivos de documentacao

entao o agent deve obrigatoriamente revisar:

- referencias em docs
- referencias em scripts
- referencias em queries SQL
- impacto em reproducao da stack

## 11. Definition Of Done

Uma alteracao so deve ser considerada consistente quando:

- a mudanca estiver alinhada com a arquitetura do projeto
- os nomes estiverem coerentes
- banco, scripts e docs estiverem consistentes entre si
- os testes afetados tiverem sido ajustados, ou a lacuna tiver sido explicitada
- nao houver artefato redundante ou referencia quebrada introduzida pela mudanca

## 12. Regra De Prudencia

Antes de aumentar complexidade com:

- novo modelo
- nova dependencia pesada
- nova camada de classificacao
- nova estrategia de treino

o agent deve responder internamente:

- isso resolve causa raiz ou mascara sintoma?
- isso vem antes ou depois da `Prioridade 0`?
- isso aumenta reprodutibilidade ou dificulta defesa tecnica do TCC?

Se a resposta apontar para aumento de complexidade sem ganho estrutural claro, a recomendacao deve ser adiar a mudanca.
