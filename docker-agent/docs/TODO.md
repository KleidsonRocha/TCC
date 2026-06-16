# TODO - Prioridades Reais Do Produto (docker-agent)

## Plano operacional - Home office para fine-tuning

Objetivo:

- Viabilizar `1-2` dias de trabalho em home office para executar o treino do modelo em uma maquina com `RTX 5060 16 GB`, preservando os dados curados do banco e garantindo retorno controlado do artefato treinado para o ambiente da empresa.

Antes do home office:

- [ ] Validar que os dados de bootstrap de regras de negocio sobem pelo repositorio e entram na criacao do banco
  - conferir no `db/init/pre_search_init.sql` a carga de `engine`, `grupo`, `subgrupo`, `brand` e `model`
  - recriar o banco em ambiente descartavel e validar se essas tabelas ficam populadas sem carga manual adicional
  - registrar quais dados sao seed do repositorio e quais dados dependem de dump/import posterior

- [ ] Fazer backup das tabelas dinamicas de fine-tuning e revisao
  - exportar `pre_search_review_interaction`
  - exportar `pre_search_fine_tuning_dataset_header`
  - exportar `pre_search_fine_tuning_dataset_record`
  - exportar `pre_search_fine_tuning_run`
  - definir e testar o procedimento de restore no banco do PC de casa

- [ ] Validar reproducao minima da stack antes de sair da empresa
  - garantir que o repositorio atualizado sobe `ollama`, `presearch-db`, `docker-agent` e `trainer`
  - garantir que o modelo base `qwen2.5:7b` pode ser puxado no `ollama`
  - garantir que o dataset revisado/exportado esta consistente para treino

- [ ] Preparar acesso remoto entre os dois PCs
  - criar acesso remoto do PC da empresa para o PC de casa
  - criar acesso remoto do PC de casa para o PC da empresa
  - testar acesso a arquivos, banco, logs e artefatos necessarios para contingencia

Em casa:

- [ ] Restaurar o banco e validar a stack no PC com GPU
  - importar o dump das tabelas dinamicas no banco local
  - subir os containers do projeto
  - validar conectividade entre `docker-agent`, `presearch-db`, `ollama` e `trainer`

- [ ] Executar o fine-tuning com `LoRA/QLoRA`
  - buildar o `trainer`
  - exportar o dataset de treino se necessario
  - rodar o treino com base em `Qwen/Qwen2.5-7B-Instruct`
  - acompanhar consumo de VRAM, tempo de treino e artefatos gerados

- [ ] Validar o artefato treinado antes de trazer de volta
  - confirmar geracao do diretorio `adapter`
  - registrar `training_summary.json`
  - empacotar o modelo no `ollama`, se necessario, para teste local
  - comparar candidato vs modelo base no benchmark/golden set

- [ ] Preparar retorno do artefato para a empresa
  - salvar o `adapter` treinado e os arquivos de apoio necessarios
  - copiar o artefato para um meio de transporte seguro ou sincronizacao controlada
  - documentar o comando de import/publicacao no PC da empresa

Entregaveis esperados no retorno:

- [ ] Dump/restauracao das tabelas dinamicas validado
- [ ] Evidencia de que o bootstrap do banco sobe os dados estruturais do dominio
- [ ] `adapter` do fine-tuning exportado
- [ ] Resumo de treino e benchmark do candidato
- [ ] Passo a passo de restauracao/publicacao do modelo no ambiente da empresa

## Fora do topo agora

- [ ] Fine-tuning da LLM
  - Nao usar treino como solucao primaria para erro de catalogo, ranking ou orquestracao

- [ ] Avaliar classificador auxiliar em portugues para slot filling
  - Considerar `BERTimbau` ou modelo equivalente apenas como apoio ao extractor deterministico
  - Usar para classificar campos como `part_query`, `brand`, `model`, `vehicle_year`, `engine`, `side` e `position` quando houver baixa confianca lexical
  - Nao substituir a LLM principal nem introduzir essa camada antes de estabilizar a `Prioridade 0`
  - So seguir se a bateria real mostrar ganho claro em extracao/normalizacao que nao compense com regra ou heuristica simples

- [ ] Seed incremental e rotinas de carga
  - Importante, mas nao antes de corrigir as falhas que ja apareceram na bateria real

- [ ] Benchmarks isolados que nao mudem decisao de produto
  - Manter como diagnostico, nao como foco principal

## Prioridade 0 - Parar erros com conviccao

- [ ] Bloquear qualquer `part_code` inventado
  - Encontrar a origem do caso real `FREIO-2010`
  - So aceitar `part_code` literal da mensagem, do contexto ou validado pelo extractor
  - Criar regressao especifica para `pastilha de freio 2010 1.0`
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md.

Objetivo:
Bloquear qualquer `part_code` inventado.

Escopo:
- Encontrar a origem do caso real `FREIO-2010`
- Aceitar `part_code` apenas quando for literal da mensagem, do contexto ou validado pelo extractor
- Criar regressao especifica para `pastilha de freio 2010 1.0`

Arquivos provaveis:
- app/core/usecases/process_agent_request.py
- app/infra/pre_search_validator_llm.py
- app/infra/pre_search_fine_tuning_format.py se houver reflexo no payload
- tests/test_rules.py
- tests/test_respond.py
- testes adicionais necessarios

Restricoes:
- Nao relaxar validacao para "fazer passar"
- Nao mexer em ranking ERP nesta tarefa

Entregavel:
- bloqueio defensivo de `part_code` inventado
- teste cobrindo o caso real e variacoes proximas
- explicacao objetiva da origem corrigida
```

- [ ] Revisar regras de catalogo que geram perguntas sem sentido
  - Corrigir `filtro de  oleo -> needs_axle`
  - Corrigir `filtro de ar do motor -> needs_axle`
  - Corrigir `filtro de combustivel -> needs_side`
  - Auditar familias similares antes da proxima bateria real
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md, db/init/pre_search_init.sql.

Objetivo:
Revisar regras de catalogo que geram perguntas sem sentido.

Escopo:
- Corrigir `filtro de oleo -> needs_axle`
- Corrigir `filtro de ar do motor -> needs_axle`
- Corrigir `filtro de combustivel -> needs_side`
- Auditar familias similares antes da proxima bateria real

Arquivos provaveis:
- db/init/pre_search_init.sql
- possiveis CSVs em db/init/csv/
- testes de regra/catalogo

Restricoes:
- Ajustar fonte de verdade no bootstrap
- Nao criar seed paralelo em docs
- Atualizar testes se naming/contrato mudar

Entregavel:
- regras corrigidas no bootstrap consolidado
- testes cobrindo filtros e familias similares
- lista curta do que foi auditado alem dos tres casos obrigatorios
```

## Prioridade 1 - Trazer a latencia para nivel operacional

- [ ] Criar caminho deterministico para casos obvios
  - Bypass da LLM quando extractor + catalogo + regras ja forem suficientes
  - Priorizar pedidos completos e follow-ups simples
  - Priorizar reducao de latencia nos fluxos mais comuns da bateria real

- [ ] Medir latencia por etapa
  - Separar `pre_search_validator`, `search_parts` e montagem de resposta
  - Identificar claramente onde esta o maior custo real
  - Manter comparacao antes e depois dos bypasses

- [ ] Reavaliar infraestrutura somente depois do bypass
  - GPU no Ollama
  - ajustes de `LLM_KEEP_ALIVE`
  - revisao de prompt somente se trouxer ganho real de tempo ou qualidade
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md.

Objetivo:
Prioridade 1 - trazer a latencia para nivel operacional.

Escopo:
- Criar caminho deterministico para casos obvios
- Medir latencia por etapa
- So depois reavaliar infraestrutura

Arquivos provaveis:
- app/core/usecases/process_agent_request.py
- app/infra/pre_search_validator_llm.py
- scripts/eval/benchmark_pre_search_latency.py
- testes de fluxo e benchmark

Restricoes:
- Nao quebrar comportamento funcional
- Priorizar bypass seguro para casos obvios
- Nao mexer em fine-tuning

Entregavel:
- bypass deterministico seguro
- medicao antes/depois
- regressao automatizada dos casos otimizados
```

## Prioridade 2 - Fazer a conversa ficar coerente ate o fim

- [ ] Corrigir follow-up com motor textual
  - Aceitar `zetec rocam`, `duratec`, `sigma` e equivalentes textuais como `engine`
  - Revalidar explicitamente o fluxo `co  xim amortecedor ecosport 2008 -> zetec rocam`

- [ ] Melhorar a resposta de `no_match`
  - Usar `conversation_state` para dizer o que realmente falta ou conflitou
  - Nao pedir novamente dados que o usuario ja informou
  - Separar `nao encontrei nada` de `sua informacao ainda esta insuficiente`

- [ ] Criar desambiguacao real quando houver muitos itens
  - Em vez de apenas listar itens, perguntar o melhor discriminador seguinte
  - Exemplos: `com ou sem ar`, `aro`, `lado`, `dianteiro ou traseiro`
  - Tratar `result_disambiguation` como etapa funcional, nao so estado salvo

- [ ] Revisar consistencia dos prompts
  - `side` deve significar `esquerdo/direito`
  - `position` deve significar `dianteiro/traseiro`
  - `axle` so deve ser usado quando fizer sentido no dominio
  - Manter perguntas curtas, diretas e especificas
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md.

Objetivo:
Prioridade 2 - fazer a conversa ficar coerente ate o fim.

Escopo:
- Corrigir follow-up com motor textual (`zetec rocam`, `duratec`, `sigma`)
- Melhorar resposta de `no_match`
- Criar desambiguacao real
- Revisar consistencia dos prompts de `side`, `position` e `axle`

Arquivos provaveis:
- app/core/usecases/process_agent_request.py
- app/infra/pre_search_validator_llm.py
- app/infra/pre_search_catalog_pg.py
- tests/test_respond.py
- tests/test_rules.py

Restricoes:
- Nao introduzir camada nova de ML
- Preservar coerencia multi-turno
- Transformar erros reais em regressao quando possivel

Entregavel:
- follow-up coerente
- `no_match` menos repetitivo
- testes cobrindo fluxo conversacional real
```

## Prioridade 3 - Melhorar a qualidade da busca

- [ ] Refinar ranking do ERP
  - Penalizar itens correlatos quando o usuario pediu a peca principal
  - Reduzir ruido de `tampa`, `mangueira`, `kit`, `parafuso`, `lampada` e similares
  - Reduzir empates de score
  - Priorizar aplicacao exata sobre familia apenas relacionada

- [ ] Corrigir normalizacao de texto e encoding
  - Eliminar saidas quebradas como `veiculo`, `oleo` e `automatico` com encoding ruim
  - Garantir titulos legiveis nas listas retornadas

- [ ] Expandir a pre-validacao lexical com seguranca
  - Melhorar cobertura de typos e abreviacoes sem aumentar falso positivo
  - Priorizar `part_query`, `vehicle_model` e motor textual
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md, docs/guide/erp_search_integration.md.

Objetivo:
Prioridade 3 - melhorar a qualidade da busca.

Escopo:
- Refinar ranking do ERP
- Corrigir normalizacao de texto e encoding
- Expandir pre-validacao lexical com seguranca

Arquivos provaveis:
- app/infra/erp_search_tools_pg.py
- app/infra/pre_search_catalog_pg.py
- docs/assets/sql/erp_search_integration_candidates_runtime.sql se houver reflexo documental
- tests/test_erp_search_tools_pg.py
- tests/test_rules.py

Restricoes:
- Nao mover SQL de integracao ERP para db/init/
- Nao piorar ruido de correlatos
- Manter foco em precisao, nao volume

Entregavel:
- ranking mais aderente
- strings/titulos sem encoding quebrado
- testes cobrindo ruido e aplicacao exata
```

## Prioridade 4 - Fechar o ciclo de qualidade com evidencias reais

- [ ] Reexecutar a bateria real apos cada bloco critico
  - bloco 1: canonizacao + `part_code` + regras de catalogo
  - bloco 2: motor textual + `no_match` + desambiguacao
  - bloco 3: ranking + latencia

- [ ] Transformar erros reais em regressao automatizada
  - Destacar pelo menos:
  - `filtro de oleo gol 2010`
  - `filtro ar motor gol 2010`
  - `filtro de combustivel gol 2010`
  - `coxim amortecedor ecosport 2008 -> zetec rocam`
  - `pastilha de freio 2010 1.0`
  - `pstilhas gol 2010`
  - `farol gol 2010`

- [ ] Consolidar os artefatos finais de avaliacao
  - manter bateria real como evidencia principal
  - manter relatorio consolidado como leitura executiva
  - manter este backlog alinhado com os achados reais
  - Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/TODO.md, scripts/README.md.

Objetivo:
Prioridade 4 - fechar o ciclo de qualidade com evidencias reais.

Escopo:
- Reexecutar a bateria real apos cada bloco critico
- Transformar erros reais em regressao automatizada
- Consolidar artefatos finais de avaliacao

Arquivos provaveis:
- scripts/eval/run_real_respond_battery.py
- scripts/eval/generate_eval_report.py
- tests/
- docs/assets/reports/
- docs/PROGRESS.md se necessario

Restricoes:
- Nao criar relatorio duplicado sem necessidade
- Evidencia principal deve continuar sendo bateria real + regressao automatizada

Entregavel:
- regressao dos casos reais listados no TODO
- artefatos de avaliacao atualizados
- resumo objetivo do antes/depois
```
