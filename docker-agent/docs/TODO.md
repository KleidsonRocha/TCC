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
  - Revalidar explicitamente o fluxo `coxim amortecedor ecosport 2008 -> zetec rocam`

- [ ] Melhorar a resposta de `no_match`
  - Usar `conversation_state` para dizer o que realmente falta ou conflitou
  - Nao pedir novamente dados que o usuario ja informou
  - Separar `nao encontrei nada` de `sua informacao ainda esta insuficiente`

- [ ] Criar desambiguacao real quando houver muitos itens
  - Em vez de apenas listar itens, perguntar o melhor discriminador seguinte
  - Exemplos: `com ou sem ar`, `aro`, `lado`, `dianteiro ou traseiro`
  - Tratar `result_disambiguation` como etapa funcional, nao so estado salvo

- [ ] Reestruturar o prompt inicial da LLM como contrato operacional
  - Organizar `_build_system_instructions` em secoes claras: papel, contrato JSON, fontes de contexto, regras de decisao e exemplos
  - Definir precedencia entre `message_text`, mensagens `user` recentes, `conversation_state`, `dictionary_seed_criteria` e `last_messages`
  - Tratar mensagens `assistant` como contexto conversacional, nao como fonte factual para preencher slots
  - Incluir exemplos minimos de saida para `ask`, `search` e `handoff`
  - Deixar explicito que o backend continua sendo a autoridade final para score, campos obrigatorios e bloqueios defensivos
  - Cobrir com regressao casos de `part_code` inventado, contaminacao por mensagem do `assistant` e conflito entre LLM e extractor deterministico

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
- Reestruturar o prompt inicial da LLM como contrato operacional
- Revisar consistencia dos prompts de `side`, `position` e `axle`

Arquivos provaveis:
- app/core/usecases/process_agent_request.py
- app/infra/pre_search_validator_llm.py
- app/infra/pre_search_fine_tuning_format.py se houver reflexo no dataset de treino
- app/infra/pre_search_catalog_pg.py
- tests/test_respond.py
- tests/test_rules.py

Restricoes:
- Nao introduzir camada nova de ML
- Preservar coerencia multi-turno
- Nao resolver falha deterministica apenas com prompt
- Manter backend como autoridade final para score, regras obrigatorias e bloqueios defensivos
- Transformar erros reais em regressao quando possivel

Entregavel:
- follow-up coerente
- `no_match` menos repetitivo
- prompt inicial mais estruturado, com precedencia de fontes e exemplos de saida
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

## Prioridade 5 - Avaliar recuperacao semantica para pedidos genericos

Objetivo:

- Complementar aliases e fuzzy matching quando o usuario descreve a funcao, o sintoma ou uma expressao popular sem citar o nome da peca.
- Recuperar familias reais do catalogo com embeddings, passar candidatos controlados para a LLM montar uma pergunta e aguardar confirmacao do usuario antes de consolidar `part_query`.
- Preservar o Redis do `docker-comm` como unica persistencia de historico e estado conversacional.

Ordem obrigatoria desta prioridade:

- iniciar somente depois de estabilizar as Prioridades 0 a 4 e registrar o baseline atual
- executar primeiro uma prova de conceito sobre as familias de `pre_search_part_type`
- nao vetorizar os itens do ERP na primeira fase
- nao promover para o runtime sem ganho mensuravel e regressao automatizada

### 5.1 Definir baseline e criterios de sucesso

- [ ] Montar dataset de avaliacao semantica separado do dataset de fine-tuning
  - incluir pedidos explicitos que o extractor atual ja resolve
  - incluir typos que devem continuar sendo resolvidos pelo fuzzy
  - incluir descricoes funcionais, sintomas e expressoes populares
  - incluir frases ambiguas com duas ou mais familias plausiveis
  - incluir mensagens fora do dominio para medir falsos positivos
  - incluir exemplos multi-turno com confirmacao, negacao, numero da opcao e `nenhuma dessas`

- [ ] Registrar o baseline antes da prova de conceito
  - medir extractor atual isolado
  - medir extractor atual + LLM atual
  - registrar acerto `top-1`, cobertura `top-3`, falso positivo, taxa de confirmacao e latencia
  - definir limites minimos de ganho para justificar a nova camada

### 5.2 Criar fonte semantica curada no catalogo

- [ ] Definir documentos semanticos vinculados a `pre_search_part_type`
  - manter `part_type_id` como identidade canonica da familia
  - manter tambem grupo, subgrupo e nome canonico para auditoria
  - separar tipos de documento como `description`, `customer_phrase`, `symptom` e `usage`
  - incluir limites negativos quando uma expressao puder confundir familias relacionadas

- [ ] Versionar o conteudo humano em CSV de bootstrap
  - criar `db/init/csv/pre_search_part_semantic_document.csv`
  - usar a chave de origem `cd_grupo + cd_subgrupo`
  - nao salvar vetores manualmente no CSV
  - revisar as descricoes com conhecimento de dominio antes de gerar embeddings
  - atualizar `db/init/pre_search_init.sql` sem criar seed paralelo em `docs/`

### 5.3 Escolher modelo e estrategia de persistencia

- [ ] Comparar modelos de embedding adequados para portugues
  - registrar nome, versao, dimensao, licenca, tamanho e latencia
  - validar expressoes reais de autopecas, nao apenas benchmark generico
  - garantir que consulta e documentos usem exatamente o mesmo modelo e versao

- [ ] Fazer a primeira prova de conceito com as familias em memoria
  - trabalhar inicialmente sobre as cerca de 338 familias, evitando infraestrutura prematura
  - pre-gerar os embeddings dos documentos no bootstrap ou em comando operacional explicito
  - medir tempo de inicializacao, memoria e latencia por consulta

- [ ] Avaliar PostgreSQL + `pgvector` apenas depois da prova de conceito
  - substituir a imagem `postgres:16-alpine` somente se a persistencia vetorial for aprovada
  - criar extensao, tabela, indice e rotina de reindexacao de forma reproduzivel
  - armazenar `embedding_model`, `embedding_version`, dimensao e data de geracao
  - definir invalidacao e reindexacao quando documento ou modelo mudar
  - nao adicionar banco vetorial separado enquanto o volume das familias nao justificar

### 5.4 Criar o recuperador semantico no `docker-agent`

- [ ] Definir uma porta de recuperacao semantica desacoplada do provedor
  - entrada: mensagem atual e contexto de desambiguacao permitido
  - saida: `part_type_id`, nome canonico, grupo, score e origem do documento
  - limitar o resultado a `top-k` pequeno e ordenado
  - permitir implementacao em memoria e futura implementacao com `pgvector`

- [ ] Encaixar a recuperacao depois de alias/fuzzy e antes da decisao conversacional
  - executar somente quando `part_query` continuar ausente ou insegura
  - nao substituir resultado exato ou fuzzy seguro
  - nao usar mensagem do `assistant` como evidencia factual de peca
  - em follow-up, restringir a busca aos candidatos pendentes quando aplicavel
  - se o recuperador falhar ou exceder timeout, continuar pelo fluxo atual sem derrubar `/respond`

- [ ] Definir politica deterministica de confianca
  - calibrar score minimo usando o dataset real
  - exigir margem minima entre primeiro e segundo candidato
  - distinguir `sem candidato`, `candidato forte` e `candidatos ambiguos`
  - na primeira versao, toda familia originada somente de embedding deve pedir confirmacao
  - impedir que score vetorial libere `search` ou valide aplicacao veicular sozinho

### 5.5 Integrar a desambiguacao ao contrato e ao Redis existente

- [ ] Estender `ConversationState` de forma retrocompativel nos dois servicos
  - adicionar campo opcional `semantic_disambiguation`
  - manter `criteria`, `pending_slot`, `pending_question` e `last_decision`
  - representar texto original, candidatos, tentativa atual, modelo e versao do embedding
  - atualizar `docker-agent/app/core/domain/models.py`
  - atualizar `docker-comm/app/core/domain/models.py`
  - revisar os schemas e o cliente HTTP do contrato `v1.0`

- [ ] Reutilizar exclusivamente a persistencia atual do `docker-comm`
  - continuar usando `conv:{conversation_id}:history`
  - continuar usando `conv:{conversation_id}:state`
  - deixar o `docker-agent` produzir o estado atualizado e o `docker-comm` persisti-lo
  - respeitar `HISTORY_LIMIT` e `SESSION_TTL_SECONDS`
  - nao criar Redis, chave de sessao ou store paralelo no `docker-agent`

- [ ] Definir ciclo de vida do estado semantico
  - criar estado ao retornar pergunta de confirmacao
  - incrementar tentativa em resposta ainda ambigua
  - limpar ao confirmar uma familia canonica
  - limpar ao negar todas as opcoes, reiniciar o pedido ou realizar handoff
  - limitar tentativas para evitar loop conversacional

### 5.6 Integrar candidatos a LLM sem transferir autoridade

- [ ] Adicionar candidatos semanticos ao payload do validador
  - informar somente familias existentes e seus identificadores
  - permitir que a LLM redija uma pergunta curta e natural
  - gerar `options` a partir dos candidatos aprovados pelo backend
  - impedir a LLM de introduzir opcao fora do conjunto recuperado
  - manter backend como autoridade sobre score, margem, campos obrigatorios e gate

- [ ] Tratar todos os caminhos de confirmacao
  - selecao pelo nome da familia
  - selecao pelo numero ou opcao da interface
  - resposta descritiva que refine os candidatos anteriores
  - negacao de uma opcao
  - `nenhuma dessas` ou mudanca de assunto
  - ambiguidade repetida com nova pergunta ou handoff apos o limite

### 5.7 Auditoria, revisao e aprendizado operacional

- [ ] Registrar evidencia semantica na fila de revisao
  - guardar modelo, versao, candidatos, scores, margens e familia confirmada
  - distinguir sugestao vetorial de criterio confirmado pelo usuario
  - nao promover automaticamente a primeira sugestao para o dataset formal
  - permitir transformar expressoes recorrentes confirmadas em alias ou documento curado

- [ ] Revisar impacto no fine-tuning
  - decidir se candidatos semanticos entram no payload dos novos exemplos
  - versionar o contrato do dataset se a forma de entrada mudar
  - nao misturar avaliacao do embedding com avaliacao do adapter da LLM

### 5.8 Testes, observabilidade e rollout

- [ ] Criar testes unitarios
  - ranking `top-k`, score minimo e margem
  - preferencia de alias/fuzzy sobre recuperacao semantica
  - fallback quando o provedor de embedding estiver indisponivel
  - limpeza e limite de tentativas do estado

- [ ] Criar testes de contrato e Redis no `docker-comm`
  - serializar e desserializar `semantic_disambiguation`
  - encaminhar o estado para o `docker-agent`
  - persistir o estado retornado usando as chaves existentes
  - aceitar respostas antigas sem o novo campo opcional

- [ ] Criar testes integrados multi-turno
  - `aquilo que evita o carro de pular -> amortecedor -> confirmar -> continuar criterios`
  - `algo que segura o carro -> opcoes ambiguas -> segunda opcao`
  - `nenhuma dessas -> pedir nova descricao`
  - confirmacao da familia seguida de pergunta por modelo, ano ou motor
  - falha de embedding mantendo o fluxo atual operacional

- [ ] Adicionar feature flags e metricas
  - iniciar com recuperacao desativada por padrao
  - oferecer modo `shadow`, calculando candidatos sem alterar a resposta
  - medir uso, acerto confirmado, rejeicao, handoff, latencia e falso positivo
  - promover gradualmente somente depois do comparativo com o baseline

### 5.9 Criterio de conclusao

- [ ] Considerar a recuperacao semantica pronta somente quando
  - melhorar de forma mensuravel pedidos genericos sem regredir pedidos explicitos
  - mantiver aliases, fuzzy, regras e gate como autoridades deterministicas
  - nao liberar pesquisa ERP a partir de similaridade vetorial sem confirmacao
  - reutilizar o Redis atual sem persistencia conversacional duplicada
  - tiver fallback seguro, testes multi-turno e observabilidade
  - tiver documentacao de bootstrap, operacao, modelo e reindexacao atualizada

Fora do escopo da primeira fase:

- embeddings para todos os itens de `soccol.item_search_candidates`
- substituicao do ranking lexical do ERP
- validacao semantica de compatibilidade entre peca e veiculo
- preenchimento automatico de `part_query` sem confirmacao do usuario
- novo banco vetorial ou nova camada de sessao

Prompt sugerido para agent:

```text
Leia obrigatoriamente: AGENTS.md, README.md, docs/DECISIONS.md, docs/PROGRESS.md,
docs/TODO.md, docs/guide/pre_search_runtime_flow.md,
docs/guide/runtime_and_bootstrap.md, docs/guide/erp_search_integration.md e
docs/training/pre_search_fine_tuning.md.

Objetivo:
Prioridade 5 - executar uma prova de conceito de recuperacao semantica para
pedidos genericos, com confirmacao multi-turno pelo Redis existente.

Restricoes:
- Nao substituir alias, fuzzy, regras, gate ou busca ERP
- Nao criar persistencia conversacional paralela
- Nao vetorizar itens do ERP na primeira fase
- Nao promover para runtime sem baseline, benchmark e regressao
- Falha do recuperador semantico deve manter o fluxo atual operacional

Entregavel:
- dataset e baseline semanticos
- documentos curados por familia
- recuperador top-k desacoplado
- desambiguacao multi-turno persistida pelo docker-comm
- testes, metricas e decisao de promover ou descartar a hipotese
```
