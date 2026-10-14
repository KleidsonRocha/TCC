# AGENTS - Regras De Trabalho No Projeto

Este arquivo define o comportamento esperado de qualquer agent que va analisar, editar, testar ou evoluir este repositorio.

O objetivo e preservar consistencia tecnica, evitar retrabalho e impedir que mudancas locais quebrem a coerencia entre runtime, banco, ERP, fine-tuning e documentacao.

Revisado em 05/10/2026. Este arquivo orienta o trabalho; o estado do produto e as prioridades continuam nos documentos indicados abaixo.

Os caminhos sem prefixo sao relativos a `docker-agent/`. `../README.md` pertence a raiz do repositorio e `../docker-comm/` pertence ao gateway. Este arquivo fica no escopo de `docker-agent/`; ao trabalhar em outro diretorio, confira tambem os `AGENTS.md` aplicaveis naquele caminho.

## 1. Leitura Obrigatoria Antes De Qualquer Mudanca

Antes de propor ou aplicar qualquer alteracao:

1. Leia `../README.md`, `README.md` e `docs/README.md` para entender a stack e localizar a documentacao.
2. Leia `docs/DECISIONS.md`, `docs/PROGRESS.md` e `docs/TODO.md` para conhecer contratos, evidencias, limites e prioridades atuais.
3. Leia `docs/guide/runtime_and_bootstrap.md` e `docs/guide/pre_search_runtime_flow.md` para entender configuracao, dependencias e fluxo ponta a ponta.
4. Identifique todas as areas afetadas e complete a leitura da matriz abaixo antes de editar. Uma tarefa pode exigir varias linhas da matriz.
5. Leia os arquivos que serao alterados, seus chamadores, contratos, configuracoes e testes relacionados. Documentacao sozinha nao substitui a inspecao do codigo.

| Area afetada | Leitura adicional obrigatoria |
| --- | --- |
| Extracao, regras, estado ou resposta do agente | `docs/guide/pre_search_runtime_flow.md`, regras de familia nos CSVs/SQL e testes de regras, API e desambiguacao. |
| Banco, catalogo, aliases ou bootstrap | `docs/guide/runtime_and_bootstrap.md`, `docs/guide/operational_commands.md`, `scripts/README.md`, `db/init/pre_search_init.sql` e seeds/scripts afetados. |
| ERP, filtros, ranking ou snapshot | `docs/guide/erp_search_integration.md`, `docs/guide/operational_commands.md`, `scripts/README.md`, `docs/assets/datasets/README.md` e contratos/avaliadores de busca. |
| Revisao, dataset, exportacao, treino ou promocao | `docs/training/pre_search_fine_tuning.md`, `docs/assets/datasets/README.md`, `scripts/README.md`, `docs/guide/operational_commands.md` e schemas/scripts/tests do ciclo afetado. |
| Gateway, Redis, Streamlit ou Omni/Convert | `../docker-comm/README.md`, `../docker-comm/docs/guia_execucao_e_implementacao.md`, decisoes atuais de canal/turno em `docs/DECISIONS.md` e schemas, rotas, stores, UI e testes dos dois servicos. |
| Configuracao, seguranca, concorrencia ou deploy | `docs/guide/runtime_and_bootstrap.md`, `docs/guide/operational_commands.md`, READMEs dos servicos afetados, `.env.example`, Compose, Dockerfile, settings e inicializacao correspondentes. |
| Testes, metricas ou relatorios do TCC | `docs/assets/datasets/README.md`, `scripts/README.md`, `docs/guide/operational_commands.md` e secoes pertinentes de `docs/HISTORICO.md`, alem dos datasets e avaliadores usados. |

### Outras Documentacoes E Divergencias

- `docs/HISTORICO.md` registra problemas anteriores, experimentos e motivos de regressoes. Consulte as secoes relacionadas ao caso; resultados antigos nao comprovam a versao atual.
- `../docker-comm/docs/estrutura.md` e `../docker-comm/docs/esqueleto.md` descrevem estrutura e escopo inicial do gateway. Podem conter caminhos, limites e propostas anteriores a integracao atual; confira-os contra codigo, README e decisoes vigentes.
- `../Documents/` contem analises e relatos antigos. Use-os como contexto quando relacionados a tarefa, sem transformar recomendacoes antigas em requisitos atuais.
- Siga referencias dos documentos relevantes ate os contratos, scripts e dados que sustentam a mudanca. Se uma leitura for truncada, leia os trechos restantes pertinentes.
- Diferencie comportamento implementado, comportamento testado localmente, implantacao confirmada e funcionalidade planejada. Diagramas com `planejado`, exemplos de configuracao e arquivos de trainer nao provam entrega operacional.
- Se documentos e codigo divergirem, identifique a divergencia, confira a decisao mais recente e a evidencia executavel. Nao copie uma regra antiga nem altere o contrato silenciosamente; reconcilie a documentacao afetada no escopo da tarefa.
- Se um arquivo citado estiver ausente, procure referencia substituta ou gerador. Nao invente conteudo nem declare validacao que depende desse arquivo.
- Instrucoes e prioridades explicitas do usuario na sessao prevalecem sobre este roteiro; preserve as demais regras aplicaveis.

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

- consultar a ordem vigente em `docs/TODO.md`, sem fixar aqui numeros de prioridades que podem ser removidos ou reorganizados
- respeitar decisoes de congelamento do baseline e de divida deterministica em `docs/DECISIONS.md`; defeitos de backend nao viram alvos de treino para a LLM mascarar
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
- `app/infra/erp_search_query.py`
- `app/infra/pre_search_dictionary_extractor.py`
- `app/core/domain/models.py`
- `app/core/domain/result_disambiguation.py`
- `app/api/schemas/contract_v1.py`
- `app/infra/pre_search_review_queue_pg.py`
- `db/init/pre_search_init.sql`
- `scripts/training/review_pre_search_queue.py`
- `scripts/training/export_pre_search_fine_tuning_dataset.py`
- `scripts/training/run_pre_search_fine_tuning_cycle.py`
- `tests/`

Quando houver impacto entre servicos, conferir tambem `../docker-comm/app/api/schemas.py`, `../docker-comm/app/api/routes/test_send.py`, `../docker-comm/app/core/usecases/process_inbound_message.py`, `../docker-comm/app/core/domain/response_stage.py`, os stores Redis, o cliente HTTP e `../docker-comm/ui/streamlit_app.py`.

Antes de editar, conferir o diff existente e preservar alteracoes do usuario. Nao incluir segredos de `.env`, credenciais ou conversas privadas em codigo, testes, documentacao ou saidas compartilhadas.

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

Em volumes existentes, atualizar um CSV nao atualiza automaticamente o banco nem o catalogo carregado pelo agente. Conferir o procedimento de aplicacao e reinicio em `docs/guide/operational_commands.md`. Preferir os scripts transacionais de atualizacao para preservar fila, datasets e snapshots; recriacao de volumes nao e um passo automatico de uma correcao de codigo.

## 6. Regras De Integracao Com O ERP

O runtime consulta:

- `soccol.item_search_candidates`
- `soccol.item_search_applications` (contrato v2: uma linha por aplicacao)

Esses objetos pertencem a camada de integracao ERP. O fallback local preserva
uma copia do mesmo contrato; o DDL externo continua separado do bootstrap local.

O modulo documental correspondente e:

- `docs/guide/erp_search_integration.md`

O DDL operacional do ERP nao e versionado neste projeto. O exportador consulta
as views instaladas; auditorias de origem podem receber uma copia local do
SQL por `scripts.eval.evaluate_erp_search --integration-sql`.

Se houver mudanca em busca ERP:

- validar compatibilidade com `app/infra/erp_search_tools_pg.py`
- nao mover SQL de integracao ERP para `db/init/`
- manter claro que isso e uma camada externa de integracao

Invariantes da busca:

- validar identidade da familia e todos os criterios veiculares exigidos na mesma aplicacao antes do ranking e do limite; nao combinar anos ou motores de aplicacoes diferentes
- comparar modelo por igualdade normalizada: `Gol` nao e `Golf`; acessorio nao substitui a familia principal
- ERP quente e fonte operacional; snapshot v2 e contingencia/reproducao, com manifestos, checksums e arquivos gzip em Git LFS
- manter `client_encoding=UTF8` na consulta e na exportacao; preservar titulos e acentos na resposta publica
- zero resultados e diferente de indisponibilidade. Preservar erros por item e nao converter falha tecnica em `no_match`
- fallback direcional: somente apos zero produtos, tentar uma vez sem `side` e `position`, preservando os demais filtros, prazo e criterios originais; informar ampliacao e pedir confirmacao da direcao
- `score` e relevancia e `confidence` e heuristica de fluxo; nenhum deles e probabilidade calibrada de compatibilidade
- diagnosticos de busca/ranking ficam na captura interna e nos logs; nao expor `search_diagnostics` ou inventario rejeitado no contrato publico

Detalhes e pesos atuais ficam em `docs/guide/erp_search_integration.md` e `docs/DECISIONS.md`; nao ajustar pesos apenas para melhorar um caso isolado sem regressao e evidencia.

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
- manter todos os turnos da mesma conversa no mesmo split e preservar o teste retido
- conferir paridade de prompt, payload, estado e regras entre exportacao, benchmark e runtime
- nao considerar pre-anotacoes ou sugestoes assistidas por IA como rotulos humanos confirmados; preservar evidencia, responsavel e status de revisao
- manter modelo ativo e candidato separados; promocao depende de comparacao controlada e possibilidade de rollback

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
- `docs/HISTORICO.md` = resumo unico dos relatorios e problemas das versoes anteriores
- `docs/TODO.md` = backlog e plano operacional
- `docs/assets/datasets/` = datasets ativos e roteiro de validacao humana
- `.tmp/eval/` = relatorios gerados, fora do Git

Regras:

- nao criar documento novo se o tema couber claramente em um documento existente
- nao deixar documento duplicado dizendo a mesma coisa com nomes diferentes
- se remover ou renomear um arquivo, atualizar referencias
- evitar misturar portugues e ingles no mesmo documento, salvo nomes tecnicos inevitaveis
- atualizar `PROGRESS.md` com o que foi implementado e efetivamente verificado; manter pendencias no `TODO.md` e motivos de mudancas de contrato em `DECISIONS.md`
- nao duplicar backlog ou historico neste `AGENTS.md`; manter aqui regras e referencias duraveis

## 9. Regras Para Testes

Toda correcao relevante de regra deve virar regressao automatizada quando fizer sentido.

Priorizar cobertura em:

- `tests/test_rules.py`
- `tests/test_process_agent_request_review_capture.py`
- testes de fluxo da API
- testes do ciclo de treino quando a mudanca tocar exportacao, promocao ou publicacao
- `tests/test_result_disambiguation.py`, `tests/test_erp_search_tools_pg.py` e `tests/test_erp_search_golden.py` quando tocar estado, busca ou ranking
- testes de `../docker-comm/tests/` quando tocar gateway, recuperacao de turno, Redis ou interface

Comandos, executados a partir do diretorio do servico correspondente:

```powershell
# docker-agent: build e suite no container Linux
.\scripts\testing\run_quality_checks.ps1

# docker-agent: validacao focada
.\scripts\testing\run_quality_checks.ps1 -PytestArgs "-q tests/test_rules.py tests/test_respond.py"
```

```bash
# Dentro do ambiente do servico, com suas dependencias instaladas
python -m pytest -q

# docker-agent: contrato SQL, com PostgreSQL de teste acessivel/configurado
python -m scripts.eval.evaluate_erp_search

# docker-agent: conferir selecao da bateria sem chamar a API
python -m scripts.eval.run_real_respond_battery --tier extended --dry-run
```

- Escolher os testes que cobrem a causa e o contrato afetado; usar bateria pelo `--target comm` quando precisar validar Redis/gateway ponta a ponta. Consultar `docs/guide/operational_commands.md` para pre-condicoes e opcoes.
- Mutation testing exige Linux/WSL/container com `fork`; consultar o guia antes de executar.
- Usar dependencias e ambiente previstos no projeto; informar quando a verificacao usa versoes diferentes.
- Registrar falhas, skips e dependencias indisponiveis. Um teste ignorado nao e evidencia de aprovacao.
- Preservar o caso real que motivou a correcao: mensagem, contexto minimo, expectativa e identificador; nao usar estoque dinamico como gabarito fixo.
- Nomes de funcoes de teste devem ser unicos. Nao enfraquecer expectativas ou regenerar datasets para ocultar uma falha; conferir geradores e anotacoes antes de sobrescrever.
- HTTP 200, contrato estrutural e compatibilidade comercial sao medidas distintas. Comparacoes quantitativas exigem registrar versao, fonte ERP/snapshot, entradas, rotulos e configuracao.

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
- isso esta alinhado com a ordem vigente do `docs/TODO.md` e com o baseline do experimento?
- isso aumenta reprodutibilidade ou dificulta defesa tecnica do TCC?

Se a resposta apontar para aumento de complexidade sem ganho estrutural claro, a recomendacao deve ser adiar a mudanca.

## 13. Estado Conversacional E Contrato Do Canal

- A mensagem atual e suas correcoes explicitas prevalecem sobre historico e sugestoes da LLM. Mensagens do assistant sao contexto, nao fatos fornecidos pelo cliente.
- Gate e proveniencia de codigo valem para cada item. Nao restaurar `part_code` apenas porque existe no estado anterior.
- Manter criterios por item, item ativo e campo pendente; compartilhar aplicacao veicular somente quando explicitamente comum. `side`, `position` e `axle` sao campos independentes.
- Alteracao dos filtros que originaram uma lista invalida candidatos e exige nova validacao/busca. Perguntas de desambiguacao devem realmente reduzir o conjunto.
- Reutilizar `ConversationState` e a persistencia Redis existente, com namespace de origem, historico limitado e TTL; nao criar store paralelo de conversa.
- O canal WhatsApp e integrado pelo Omni/Convert. Webhook proprio ou cliente direto da Meta nao fazem parte do escopo atual.
- No `POST /test/send`, a primeira chamada inicia o turno; consultas posteriores por `trace_id` recuperam o mesmo processamento, sem repetir inferencia ou gravacao do turno. Preservar concessao do worker, renovacao e retencao do resultado no Redis.
- `status=processing` exige espera/consulta; enviar resposta e usar `stage` somente com `status=completed`.
- Prioridade de `stage`: handoff -> `transfer_to_human`; pergunta -> `more_info`; produtos sem pergunta/handoff -> `mostrar_produtos`; demais -> `fallback`.
- Preservar `actions`, `items`, `items_text` e opcoes no `reply` conforme o contrato. Nao exigir telefone quando o intermediario fornece identificador estavel da conversa.
- A chave temporaria atual nao equivale a idempotencia completa por ID da mensagem de origem. Conferir os limites documentados antes de alterar deduplicacao, retry ou identidade de turno.

## 14. Seguranca, Concorrencia E Operacao

- Em producao, preservar a exigencia de `REVIEW_API_KEY` e `RESPOND_GATEWAY_API_KEY`. O gateway envia `AGENT_GATEWAY_API_KEY` como `X-Agent-Gateway-Key`; revisao usa `X-Review-Key`.
- Preservar validacoes de tamanho de mensagem, historico, itens e candidatos nos schemas. Mudancas de limites exigem verificar os consumidores dos dois servicos.
- Inferencia, PostgreSQL e gravacao de revisao nao podem bloquear o event loop. Manter workers limitados, timeouts externos, `statement_timeout` e auditoria isolada por requisicao.
- `/health` verifica o processo sem I/O externo; `/ready` verifica dependencias. Warm-up da LLM nao deve bloquear o startup HTTP.
- Na VPS, manter servicos internos em loopback/rede Docker, Redis sem porta publica e Nginx como entrada publica. Conferir Compose e ambiente real antes de mudar portas.
- Alteracao local nao comprova deploy. Registrar separadamente verificacao local e verificacao na VPS/canal, sem declarar implantacao ou aceite comercial a partir de testes unitarios.
- Antes de aplicar mudancas persistentes em banco, snapshot ou deploy relevante, conferir alvo, backup manual e procedimento de recuperacao descritos na documentacao operacional.
