---
marp: true
paginate: true
theme: default
title: Apresentacao do Andamento do Projeto
---

# Sistema de Atendimento Inteligente para Pesquisa de Pecas

## Apresentacao do que foi entregue ate o momento

- Data de referencia: 13/03/2026
- Estrutura atual: `docker-comm` + `docker-agent`
- Foco desta apresentacao:
  - arquitetura da solucao
  - principais partes implementadas
  - como a LLM foi montada
  - como o validador funciona
  - proximos passos

---

# Objetivo do Projeto

Construir um sistema modular para atendimento e pesquisa de pecas automotivas, separando claramente:

- transporte e sessao da conversa
- interpretacao da mensagem
- validacao do pre-search
- busca de itens
- decisao da resposta ao usuario

Escolha de arquitetura:

- evitar acoplamento entre canal, regra de negocio e IA
- permitir evolucao incremental sem reescrever a base
- manter rastreabilidade via contrato, logs e `trace_id`

---

# Visao Geral da Arquitetura Atual

Fluxo principal:

`Usuario/Canal -> docker-comm -> docker-agent -> LLM + Catalogo -> search_parts -> resposta`

Componentes em runtime hoje:

- `docker-comm`
  - FastAPI
  - Redis para historico curto
- `docker-agent`
  - FastAPI
  - validador de pre-search
  - regras de decisao
- apoio do `docker-agent`
  - Ollama para LLM local
  - Postgres para catalogo de pre-search

---

# Estrutura do Repositorio

Organizacao atual:

- `Documents/`
  - visao macro, status e planejamento
- `docker-comm/`
  - gateway/orquestrador
- `docker-agent/`
  - motor de decisao e pre-search

Padrao interno adotado nos servicos:

- `app/api`
- `app/core/domain`
- `app/core/usecases`
- `app/core/ports`
- `app/infra`

Essa divisao facilita manutencao, testes e troca de componentes.

---

# Parte 1 - Como foi feito o `docker-comm`

Papel do `docker-comm`:

- receber a mensagem por HTTP
- validar a entrada
- recuperar contexto curto no Redis
- montar o contrato tecnico v1.0
- chamar o `docker-agent`
- devolver resposta simplificada ao chamador

Principais decisoes de implementacao:

- FastAPI para API e ciclo de vida da aplicacao
- Redis para historico curto por conversa
- `httpx` para chamada ao agent
- identificador interno por origem:
  - `source:conversation_id`
- fallback operacional para timeout e indisponibilidade do agent

---

# Parte 1 - Fluxo interno do `docker-comm`

Passo a passo:

1. recebe `POST /test/send`
2. valida `text`
3. normaliza `branch_id`
4. monta `trace_id`
5. aplica namespace interno da conversa
6. carrega historico no Redis
7. envia payload padronizado ao `docker-agent`
8. persiste nova interacao no Redis
9. devolve `reply`, `actions`, `handoff` e `confidence`

Ganhos desse desenho:

- o gateway nao concentra inteligencia de negocio
- o transporte fica desacoplado do motor de decisao
- novos canais podem ser conectados sem alterar o agent

---

# Parte 2 - Como foi feito o `docker-agent`

Papel do `docker-agent`:

- receber o contrato v1.0
- validar a mensagem
- interpretar o pedido de pre-search
- decidir entre `search`, `ask` ou `handoff`
- chamar a busca
- retornar resposta estruturada

Componentes centrais:

- `ProcessAgentRequestUseCase`
- `LLMPreSearchValidator`
- `DictionaryPreSearchExtractor`
- `PostgresPreSearchCatalogProvider`
- `ToolsPort` com `search_parts`

Resultado entregue ao `docker-comm`:

- `reply.text`
- `actions`
- `handoff`
- `confidence`
- `tool_trace`

---

# Contrato Tecnico Entre os Servicos

Request enviado ao agent:

- `schema_version`
- `trace_id`
- `conversation_id`
- `channel.name`
- `message.text`
- `context.last_messages`
- `runtime.locale`
- `runtime.timezone`
- `business.branch_id`

Response do agent:

- `reply.text`
- `actions`
- `handoff`
- `confidence`
- `tool_trace`

Motivo dessa escolha:

- padronizar a integracao
- permitir rastreabilidade
- manter independencia entre servicos

---

# Como a LLM esta montada

O modulo principal da IA hoje e o `LLMPreSearchValidator`.

Arquitetura adotada:

- modelo local servido por Ollama
- endpoint principal: `/api/chat`
- fallback automatico: `/api/generate`
- resposta obrigatoriamente em JSON estruturado
- temperatura baixa para reduzir variacao
- suporte a `last_messages` para contexto

Configuracao atual prevista no projeto:

- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_MS`
- `LLM_TEMPERATURE`
- `LLM_NUM_PREDICT`
- `LLM_THINK`

---

# O que a LLM recebe

A chamada para a LLM nao envia apenas o texto do usuario.

Entrada enviada para o modelo:

- `message_text`
- `last_messages`
- `dictionary_seed_criteria`
- `score_policy`

O `dictionary_seed_criteria` leva para a LLM os slots extraidos de forma deterministica.

O `score_policy` informa:

- pesos por criterio
- score minimo para autorizar `search`
- campos que ainda faltam
- restricoes para a primeira decisao

Objetivo:

- ancorar a resposta da LLM em regras e sinais concretos
- reduzir ambiguidade e resposta fora do contrato

---

# Parte 3 - Extracao Deterministica Antes da LLM

Antes de chamar a LLM, o sistema roda o `DictionaryPreSearchExtractor`.

O que ele extrai:

- `part_query`
- `part_code`
- `vehicle_brand`
- `vehicle_model`
- `vehicle_year`
- `engine`
- `side`
- `position`
- `axle`
- `quantity`

Como ele faz isso:

- aliases de peca
- aliases de marca e modelo
- regex para ano, motor e codigo
- leitura do contexto anterior da conversa

Motivacao:

- reduzir dependencia exclusiva da LLM
- melhorar consistencia
- reaproveitar conhecimento do catalogo

---

# Parte 4 - Como o Validador Funciona

Pipeline atual do validador:

1. extrai criterios de forma deterministica
2. monta instrucoes do sistema para a LLM
3. envia o contexto e a seed deterministica
4. recebe JSON com `decision`, `criteria`, `missing_fields`, `next_question` e `confidence`
5. normaliza e corrige os campos retornados
6. mergeia o resultado da LLM com a extracao deterministica
7. reaplica regras de negocio e score
8. devolve o resultado final para o use case

Saidas possiveis:

- `search`
- `ask`
- `handoff`

---

# Regras de Decisao do Validador

Exemplos de regra implementada:

- sem `part_query` e sem `part_code` -> `ask`
- com `part_code` valido -> `search`
- se faltam campos obrigatorios para aquela peca -> `ask`
- se o score estiver abaixo do minimo -> `ask`
- se a LLM falhar ou vier inconsistente -> fallback controlado
- se a LLM estiver indisponivel -> HTTP 503

O validador tambem resolve:

- `missing_fields`
- `next_question`
- `confidence`

Assim, o agent nao apenas "entende a frase":

- ele decide se ja pode buscar
- ou se precisa perguntar melhor antes

---

# Catalogo de Pre-Search no Postgres

O catalogo atual e a base de conhecimento estruturada do sistema.

Ele armazena:

- marcas e aliases
- modelos e aliases
- tipos de peca e aliases
- regras por tipo de peca
- motores por modelo
- tokens invalidos
- pesos de score
- politica de decisao

Caracteristicas do desenho:

- banco em modo strict
- fonte unica da verdade
- bootstrap por `db/init/001_pre_search_catalog.sql`
- suporte a carga por CSV real

---

# Score e Gate de Decisao

O pre-search nao depende apenas da intuicao da LLM.

Existe um gate de pontuacao:

- cada criterio possui peso
- existe um `min_score_to_search`
- `vehicle_brand` so pontua quando estiver explicita
- `part_code` pode liberar `search` mesmo com score baixo

Exemplo de uso pratico:

- modelo + ano + peca podem ser suficientes para seguir
- peca generica sem contexto suficiente vira `ask`
- peca com regra de lado, motor ou posicao gera pergunta de refinamento

Esse desenho torna a decisao mais auditavel e menos "caixa preta".

---

# Busca Atual e Pos-Busca

Depois da validacao, o agent chama `search_parts`.

Estado atual:

- a busca ainda esta mockada
- serve para validar o fluxo ponta a ponta

Comportamento atual do mock:

- ambiguidade -> retorna mais de um item
- item unico -> resposta direta
- sem resultado -> `handoff`

Mesmo com busca mock, o pos-busca ja testa a logica de resposta:

- pedir refinamento
- mostrar opcoes
- acionar handoff

---

# Avaliacao e Testes

O projeto ja possui testes automatizados e um dataset de avaliacao do pre-search.

No `docker-comm`:

- regras de validacao
- endpoint `/test/send`
- namespace de conversa por origem

No `docker-agent`:

- validacao de contrato
- regras do mock de busca
- uso do contexto anterior
- comportamento de `ask`, `search` e `handoff`

Avaliacao MVP do validador:

- dataset em `docs/pre_search_eval_dataset_mvp.json`
- metricas:
  - `decision_accuracy_pct`
  - `slot_extraction_accuracy_pct`
  - `next_question_utility_pct`

---

# O que ja foi entregue ate aqui

Entregas consolidadas:

- arquitetura modular com dois servicos
- gateway funcional com contexto em Redis
- contrato tecnico entre servicos
- agent com resposta estruturada
- validador de pre-search com LLM
- extracao deterministica antes da IA
- catalogo em Postgres como base de conhecimento
- score configuravel para decisao
- logs estruturados e `trace_id`
- scripts de carga e avaliacao
- ambiente Docker para execucao local

Em resumo:

- a base do sistema ja esta operacional
- a camada de pre-search ja esta tecnicamente avancada
- a principal pendencia funcional e a busca real de pecas

---

# Principais Limitacoes Atuais

Pontos que ainda limitam a maturidade da solucao:

- `search_parts` ainda e mock
- documentacao macro da raiz esta atrasada em relacao ao codigo
- ambiente local de testes precisa ser padronizado
- auditoria persistente ainda nao foi implementada no `docker-comm`

Mesmo assim, a estrutura atual ja sustenta:

- testes ponta a ponta
- evolucao incremental
- substituicao controlada de componentes

---

# Proximos Passos

Prioridades recomendadas:

1. substituir `search_parts` mock por integracao real
2. conectar a busca a base/catalogo oficial ou servico dedicado
3. ampliar o dataset de avaliacao do pre-search
4. melhorar a reprodutibilidade do ambiente de testes
5. alinhar `Documents/estado_atual.md` e `Documents/proximos_passos.md` ao codigo real
6. evoluir observabilidade, auditoria e metricas operacionais

Fechamento:

- a arquitetura base ja esta pronta
- o pre-search inteligente ja esta implementado
- o proximo salto do projeto e transformar a busca em producao real
