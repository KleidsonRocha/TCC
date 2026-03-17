# Historico de Problemas e Solucoes

Data de referencia: 2026-03-17

## Objetivo deste documento

Registrar os principais problemas encontrados durante a evolucao do `docker-agent` e do `docker-comm`, as causas identificadas e as solucoes adotadas ate o momento.

O foco deste historico e:
- busca real de pecas no ERP
- validacao pre-search
- fluxo conversacional entre mensagens
- persistencia de estado por conversa
- riscos e pendencias ainda abertas

## 1. Busca SQL inicial muito lenta

### Problema

A primeira versao da view `soccol.item_search_candidates` estava funcional em termos de dados, mas muito lenta para uso em runtime.

Resultados observados:
- `SELECT * FROM soccol.item_search_candidates LIMIT 10` em torno de `9s`
- `EXPLAIN ANALYZE` mostrando custo alto na agregacao de `produto_veiculos`
- `Sort` e `GroupAggregate` pesados sobre volume grande de linhas

### Causa identificada

A view original recomputava em tempo de consulta:
- agregacoes veiculares
- joins extensos
- campos textuais muito grandes
- colunas demais para consultas simples

### Solucao aplicada

Foi criada uma versao otimizada em camadas:
- `soccol.item_vehicle_model_agg_mv`
- `soccol.item_vehicle_agg_mv`
- `soccol.item_search_candidates_mv`
- `soccol.item_search_candidates` como view fina por cima

Arquivo criado:
- `docker-agent/docs/assets/sql/erp_item_search_candidates_runtime_v2.sql`

Resultado observado:
- `SELECT ... LIMIT 10` caiu para aproximadamente `1.8s`
- consultas filtradas reais ficaram na faixa de centenas de milissegundos

## 2. Necessidade de validar a qualidade da busca com consultas reais

### Problema

Nao bastava medir `LIMIT 10`; era necessario validar ranking e desempenho com casos reais do dominio.

### Solucao aplicada

Foram montadas queries reais de validacao para cenarios como:
- `coxim ecosport 2008 1.6`
- `pastilha traseira corolla 2018`
- `amortecedor onix`
- `trambulador sandero 2012`
- busca por codigo exato
- tentativa de fuzzy com erro de digitacao

### Resultado

Casos estruturados tiveram tempo e qualidade aceitaveis para integracao:
- `coxim ecosport 2008 1.6`: ~`0.104s`
- `pastilha traseira corolla 2018`: ~`0.206s`
- `amortecedor/onix`: ~`0.346s`
- `trambulador sandero`: ~`0.22s`

Problemas identificados nessa fase:
- muitos empates no score
- match amplo demais por substring
- fuzzy em `search_text` grande nao serviu para runtime

## 3. Credenciais do ERP nao podiam ficar hardcoded

### Problema

Foi necessario conectar o `docker-agent` ao banco do ERP, mas sem risco de vazar credenciais em commit.

### Solucao aplicada

Foram introduzidas variaveis `ERP_DB_*`:
- `docker-agent/app/config.py`
- `docker-agent/.env.example`
- `docker-agent/docker-compose.yml`
- `docker-agent/README.md`

As credenciais reais foram colocadas apenas no `.env` local, que ja estava fora do versionamento.

## 4. Runtime ainda dependia de mock para pesquisa

### Problema

O fluxo principal do agent ainda estava baseado em `MockTools`, apesar de a consulta real ao ERP ja estar disponivel.

### Solucao aplicada

Foi implementado o backend real de busca no ERP:
- `docker-agent/app/infra/erp_search_tools_pg.py`

Foram ajustados:
- `search_parts` para receber `SearchCriteria`
- `main.py` para resolver runtime real com ERP
- `process_agent_request.py` para passar criterios estruturados
- tratamento de erro `503` para indisponibilidade da busca

### Resultado

O fluxo principal passou a usar o ERP real quando `ERP_DB_ENABLED=true`.

## 5. Era necessario testar o fluxo real no ERP

### Problema

A integracao precisava ser validada com dados reais e nao apenas por teste unitario.

### Solucao aplicada

Foi executada busca real via `search_parts` usando a view do ERP.

Resultados observados:
- `coxim ecosport 2008 1.6`: ~`234ms`
- `pastilha traseira corolla 2018`: ~`269ms`
- `trambulador sandero 2012`: ~`279ms`

Conclusao:
- a busca ERP ficou viavel para runtime
- o principal gargalo passou a ser a LLM, nao o banco

## 6. O agent perguntava motorizacao mesmo quando ela ja estava informada

### Problema

Em cenarios com multiplos itens, o fluxo fazia pergunta fixa por motor, mesmo quando:
- a motorizacao ja estava presente na mensagem
- outro discriminador seria mais util

### Causa identificada

O branch de multiplos resultados em `ProcessAgentRequestUseCase` tinha uma pergunta fixa por `engine`.

### Solucao aplicada

Esse comportamento foi removido.

Novo comportamento:
- o branch de multiplos resultados retorna apenas `show_items`
- o estado da conversa guarda que ainda existe desambiguacao pendente

## 7. O follow-up perdia contexto entre mensagens curtas

### Problema

Quando o usuario respondia algo curto como:
- `1.6`
- `dianteiro`
- `traseiro`

o agent podia perder:
- `part_query`
- `vehicle_model`
- demais slots ja capturados anteriormente

### Causa identificada

O sistema dependia demais de:
- `last_messages` em texto bruto
- inferencia da LLM em cada turno

Nao havia estado estruturado da conversa persistido fora da LLM.

### Solucao aplicada

Foi introduzido `conversation_state` no contrato entre `docker-comm` e `docker-agent`.

No `docker-agent`:
- o contrato HTTP passou a aceitar e retornar `conversation_state`
- o validator passou a receber esse estado
- o validator passou a reutilizar criterios anteriores quando existe `pending_slot`

No `docker-comm`:
- o estado passou a ser persistido no Redis por conversa
- o estado e enviado ao `docker-agent` em cada nova mensagem
- o estado retornado pelo agent e salvo novamente

### Resultado

O fluxo ficou mais consistente para follow-ups e mais alinhado com uso multi-canal.

## 8. Mensagens do assistant estavam contaminando a extracao lexical

### Problema

Ao reconstruir contexto, o extractor podia usar mensagens do assistente e isso podia introduzir ruido artificial no texto analisado.

### Solucao aplicada

O `DictionaryPreSearchExtractor` foi ajustado para usar apenas mensagens com `role=user` ao montar o contexto auxiliar.

### Resultado

O seed deterministico passou a refletir melhor o que o usuario realmente informou.

## 9. O gargalo principal passou a ser a LLM

### Problema

Nos testes reais, a busca no ERP terminou rapido, mas a chamada ao Ollama levou dezenas de segundos.

Resultados observados:
- varias chamadas na faixa de `22s` a `30s`
- o tempo total de `/respond` ficou dominado pela LLM

### Conclusao tecnica

Neste ponto, o banco deixou de ser o principal problema.

O maior risco operacional passou a ser:
- latencia do `pre_search_validator`
- experiencia ruim de conversa

### Status

Ainda pendente de otimizacao.

## 10. A liberacao para `search` ficou permissiva demais

### Problema

Casos como:
- `quero os amortecedor da ecosport`

estao sendo liberados para busca com poucos campos, porque o score atual ja ultrapassa o minimo configurado.

### Causa identificada

Com a politica atual:
- `part_query` tem peso alto
- `vehicle_model` tem peso alto
- `min_score_to_search` esta baixo o suficiente para liberar `search` cedo

### Resultado observado

Casos com pouca especificidade passam para busca quando talvez o ideal fosse perguntar mais um dado.

### Status

Ainda pendente de ajuste.

## 11. A proxima pergunta nem sempre e a melhor pergunta

### Problema

Em alguns casos, o agent perguntou algo generico ou pouco util, mesmo quando ja havia informacao suficiente para escolher um slot mais relevante.

Exemplo observado:
- quando a peca ja esta clara, a proxima pergunta mais util pode ser `vehicle_model`
- porem a pergunta devolvida pode ser vaga ou desalinhada

### Causa identificada

Faltam duas camadas:
- melhor cobertura lexical no seed
- melhor politica para selecionar o proximo slot de desambiguacao

### Status

Ainda pendente de ajuste.

## 12. Divergencias entre alias e normalizacao lexical

### Problema

Alguns termos do usuario nao casam diretamente com o catalogo por variacao simples, por exemplo:
- singular/plural
- pequenas diferencas de escrita

### Exemplo observado

`batente` vs `batentes`

### Solucao parcial

O tema foi registrado no backlog como correcao de impacto medio e parte da estrategia futura de pre-validacao lexical antes da LLM.

### Status

Ainda pendente de implementacao.

## 13. Persistencia de estado conversacional para multi-canal

### Problema

O projeto precisava suportar varios canais e manter historico por conversa sem depender da memoria implicita da LLM.

### Solucao aplicada

O `docker-comm` passou a assumir o papel de memoria operacional:
- historico curto por conversa
- `conversation_state` por conversa
- montagem do payload completo para o `docker-agent`

Chave tecnica:
- o estado fica fora da LLM
- a LLM recebe contexto montado pelo sistema

## 14. Testes automatizados atualizados

### Solucao aplicada

Foram adicionados ou ajustados testes para cobrir:
- busca ERP real no `docker-agent`
- contrato com `conversation_state`
- persistencia de estado no `docker-comm`
- branch de multiplos resultados sem pergunta fixa por motor
- extracao ignorando mensagens do assistant

Resultados validados em Docker:
- `docker-agent`: `54 passed`
- `docker-comm`: `15 passed`

## 15. Documentacao operacional e backlog

### Solucao aplicada

O backlog foi reorganizado com foco no que realmente passou a ser prioritario:
- reduzir latencia da LLM
- endurecer o gate de liberacao para `search`
- revisar regras obrigatorias por familia de peca
- melhorar a escolha da proxima pergunta
- melhorar cobertura lexical do catalogo
- refinar relevancia da busca ERP

Arquivo atualizado:
- `docker-agent/docs/TODO.md`

## Situacao atual resumida

### Resolvido

- conexao real do `docker-agent` ao ERP via `.env`
- busca SQL otimizada com runtime `v2`
- `search_parts` real integrado ao fluxo principal
- persistencia de `conversation_state` entre `docker-comm` e `docker-agent`
- remocao da pergunta fixa por motorizacao em multiplos resultados
- isolamento melhor do contexto textual do usuario
- ampliacao de testes automatizados

### Ainda aberto

- latencia alta do Ollama
- liberacao excessiva para `search` em alguns cenarios
- proxima pergunta nem sempre e a mais util
- cobertura lexical insuficiente para algumas familias/variacoes
- refinamento fino do ranking ERP

## Observacao final

O projeto ja saiu da fase de prova de conceito para uma fase de calibracao operacional.

Os principais blocos estruturais foram resolvidos:
- integracao real com ERP
- contrato estruturado de busca
- memoria conversacional por canal

O trabalho agora esta concentrado em qualidade de decisao:
- quando perguntar
- quando pesquisar
- qual pergunta fazer
- como reduzir latencia
