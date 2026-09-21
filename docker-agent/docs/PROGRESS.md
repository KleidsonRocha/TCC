# Progresso Do Projeto

Estado em 21/09/2026. Historico de problemas, benchmarks e relatorios em
[HISTORICO.md](HISTORICO.md); pendencias e criterios de aceite em
[TODO.md](TODO.md). Resultados locais nao encerram a validacao na VPS.

## Estado Atual

- API `/respond` integra catalogo PostgreSQL, extracao deterministica,
  `deterministic_ask`, `deterministic_bypass` e LLM residual via Ollama.
- Busca e desambiguacao usam candidatos reais e estado conversacional
  persistido pelo `docker-comm` no Redis. Contrato admite `items[]`, com
  correcoes por item ainda pendentes no backlog.
- Revisao humana por conversa/turno, historico de revisoes, promocao e
  exportacao do dataset implementados. Trainer LoRA/QLoRA preparado;
  ainda sem evidencia de run concluida ou de ganho de adapter.

## Negacao, Substituicao E Conflito Antes Da Busca

- O extractor resolve a troca explicita para a parte afirmativa, ignora a
  direcao negada e nao emite clausulas negativas em `items[]`.
- Negacao ou correcao sem substituicao comprovada interrompe a busca com a
  pergunta `intent_resolution`; conflito como `Honda Gol` usa
  `vehicle_identity`.
- O bootstrap passou a aplicar `vehicle_model_brand.csv` diretamente em
  `pre_search_model.brand_id`. Modelos sem mapeamento curado continuam como
  `SEM_MARCA_MAPEADA`, sem inferencia por texto.
- A revisao humana promoveu 1.922 relacoes adicionais, deixando
  `vehicle_model_brand.csv` com 1.971 vinculos. A aplicacao no catalogo local
  atualizou 1.922 registros; a conferencia resultou em 1.971 modelos
  vinculados e 1.523 em `SEM_MARCA_MAPEADA`.
- A auditoria reproduzivel restante em
  `.tmp/catalog/model_brand_review_after_import.csv` possui 5 P1, 43 P2 e
  1.475 P3 pela recorrencia no seed de motores. A fila sera usada para
  promover somente relacoes confirmadas para `vehicle_model_brand.csv`.
- Golden set, bateria estrutural e testes unitarios receberam os quatro casos
  automotivos de regressao. Em 16/09, a suite Docker aprovou 369 testes e o
  golden da LLM aprovou 25/25 casos, incluindo negacao, substituicao e conflito.

## Itens Com Aplicacoes Veiculares Distintas

- A extracao multi-item conserva a identidade completa de cada item e nao
  propaga marca, modelo, ano ou motor de uma clausula para outra.
- Aplicacao comum no fim do pedido continua suportada quando declarada
  explicitamente, por exemplo `radiador e pastilha para Gol 2010 1.0`.
- Foram adicionados casos unitarios e tres cenarios estruturais para veiculos
  distintos, ausencia de contexto e aplicacao comum; todos foram executados
  com sucesso em 16/09.

## Follow-Up De Motor E Listas Comerciais

- O runtime trata motor textual como opcao do catalogo durante uma pergunta
  pendente: `BE`, `Zetec Rocam`, `Duratec`, `Duratec HE`, `Sigma`, `EA111` e
  `EA211` sao validados pelo modelo e, quando existir, pelo intervalo de ano.
- A decomposicao multi-item usa aliases nao sobrepostos do catalogo como
  fronteiras. Quantidade e atributos permanecem no item correspondente;
  aplicacao comum so e herdada sem identidade veicular concorrente.
- As regressões de `real_005`, `real_052`, `real_055`, `real_067` e `real_081`
  foram executadas com `tests/test_rules.py`: 146 aprovados em 17/09. A suite
  completa e a bateria longa continuam pendentes para o fechamento da
  Prioridade 2.

## Contrato Residual E Linguagem Publica

- O payload enviado a LLM residual separa a mensagem atual, seed, estado,
  mensagens anteriores do usuario e contexto do assistant, com precedencia
  declarada. O backend permanece responsavel pela decisao final.
- Perguntas direcionais usam lado esquerdo/direito, posicao dianteiro/traseiro
  e eixo dianteiro/traseiro. A desambiguacao normaliza genero e equivalentes
  em ingles sem confundir eixo com posicao.
- Os testes focados de regras e desambiguacao aprovaram 165 casos em 17/09.

## Correcao De Criterios Durante A Desambiguacao

- Candidatos de desambiguacao agora pertencem aos filtros que os originaram.
  Se o cliente substituir modelo, ano, motor, lado, posicao, eixo, variante,
  marca, marca preferida ou codigo, o runtime elimina a lista pendente e volta
  ao gate de validacao antes de consultar o ERP.
- A correcao `radiador Gol 2010 1.0` para `Corsa 2011 1.4` conserva somente a
  familia omitida na frase de correcao; os atributos do Gol nao sao reutilizados
  como candidatos nem como resultados de busca.
- Foram incluídas regressao unitária, caso no golden set e cenário estrutural
  multi-turno. Os dois turnos foram aprovados em 16/09.

## Identidade E Aplicacao ERP Corrigidas Em 14/09/2026

- Contrato v2: `soccol.item_search_candidates` e `soccol.item_search_applications`.
- Familia validada antes do ranking; radiador nao aceita tampa, kit ou mangueira
  como peca principal. Cinco aliases de tampa/mangueira no CSV e catalogo local.
- Modelo exato (`Gol` != `Golf`); marca, ano, motor e versao coincidem na mesma
  aplicacao. Intervalos separados nao sao unidos; ano desconhecido nao e fim aberto.
- Motores, injecoes e transmissoes pertencem a aplicacao da peca. Somente
  aplicacoes aprovadas fornecem atributos para desambiguacao.
- Nome completo e titulo do proprio item fornecem lado, eixo e posicao.

Evidencias da correcao: 343 testes; 38 casos automotivos de SQL executados
contra integracao e copia do snapshot (76/76). `audit_only_real` aceita somente
`AUD-REAL`, rejeitando `AUD-GOLF`, `AUD-CROSS` e `AUD-CAP`. Golden de pre-search
cobre tampa do radiador e identidade de Golf.

Em 16/09, a consulta online passou a abrir o PostgreSQL do ERP com
`client_encoding=UTF8`, igual ao exportador do snapshot. Isso corrigiu um JSON
em WIN1252 que fazia o driver Python acionar o fallback: a bateria real voltou
a obter quatro radiadores para Gol 2010 1.0 diretamente por `erp_postgres`;
a correcao para Corsa 2011 1.4 tambem consultou o ERP e retornou um item.
Na mesma validacao, a suite completa aprovou 369 testes e o golden residual da
LLM aprovou 25/25 casos. A repeticao na VPS continua necessaria.

Snapshot local: **52.798 itens e 1.776.907 aplicacoes**, exportado do banco
quente em 14/09/2026. Carga validada com rollback e instalada com backup.
API real validada para radiador Gol, tampa, coxim EcoSport e radiador Golf;
resultados e limites em [HISTORICO](HISTORICO.md).

O usuario atualizou o SQL no banco quente. A exportacao somente de leitura
de 14/09, 17:48 UTC, confirmou as duas views: 52.798 itens e 1.779.443
aplicacoes. Essa copia de verificacao ficou em `.tmp/`, preservando o snapshot
versionado anterior. Implantacao e verificacao na VPS continuam no [TODO](TODO.md).

## Follow-ups Deterministicos Corrigidos Em 11/09/2026

Follow-up `2008` preserva ano e contexto do carro; respostas de direcao
respeitam o campo pendente. Coxins exigem posicao, nao eixo; pastilhas nao
exigem motor como campo obrigatorio. Mudancas no catalogo local, CSVs e
regressoes; propagacao na VPS ainda precisa ser confirmada.

## Organizacao De Banco E Documentacao Em 14/09/2026

- `pre_search_init.sql` concentra catalogo, revisao, treino e carga do fallback;
  instalador extrai apenas o bloco de busca para volumes existentes.
- Exportador consulta as views do ERP em transacao somente de leitura,
  com ordem explicita de colunas e UTF-8; dispensa arquivo DDL no checkout.
- Snapshot v2 e manifestos permanecem versionados, com gzip no Git LFS.
- Relatorios antigos e backlog legado consolidados em `HISTORICO.md`;
  novos resultados gerados em `.tmp/eval/`, ignorados pelo Git.
- Testes padrao usam o contrato e COPY; `--integration-sql` permite repetir
  auditoria das relacoes de origem com copia local do SQL externo.

Validacao da reorganizacao: **343 testes aprovados** e **114/114 verificacoes
SQL** (38 casos no contrato, no COPY e nos SELECTs externos fornecidos).
Carga integral pelo instalador consolidado validada com rollback: 52.798
itens e 1.776.907 aplicacoes. Evidencias locais em `.tmp/eval/cleanup_tests.xml`
e `.tmp/eval/cleanup_integration_report.json`.

Bootstrap completo tambem passou em PostgreSQL 16 descartavel, isolado e sem
reutilizar volume: 338 tipos de peca do seed, 52.798 itens, 1.776.907 aplicacoes,
zero aplicacoes orfas e fila de revisao vazia. Os 15 Markdown conferidos nao
tinham links locais quebrados. Smoke do gerador produziu JSON/Markdown em
`.tmp/eval/`. Hashes dos dois arquivos LFS e manifestos conferidos contra o
indice Git: nenhum dos quatro arquivos preparados pelo usuario foi alterado.

## Desambiguacao De Resultados Concluida Localmente

Desambiguacao revisada em 16 e 17/09: atributos incompletos ou com uma opcao
comum a todos os candidatos deixam de gerar perguntas. Ate dez resultados sao
apresentados diretamente; a consulta preserva ate 50 candidatos e pagina o
excedente em grupos de dez. Valores equivalentes sao agrupados; resposta nao
compreendida troca o discriminador ou mostra a lista. Negacao de codigo nunca
seleciona o item negado. Novo filtro explicito fora das opcoes invalida os
candidatos antes de nova validacao e consulta. Os testes focados cobrem
serializacao de `ConversationState`, selecao, negacao, pagina seguinte, troca de
assunto e limite de tentativas no mesmo `ConversationState`.

## Pendencias Principais

Tambem faltam motor textual, avaliacao comercial do ranking, paridade
treino/runtime e validacao da versao atual na VPS. O teste visual confirmou a
nova pergunta de identidade de `coxim`, mas a resposta sugerida `zetec rocam`
ainda nao foi aceita pelo follow-up e repetiu a pergunta de motorizacao.
O [TODO](TODO.md) concentra o trabalho restante; reorganizar arquivos nao
altera a classificacao de prontidao comercial.

## Disponibilidade Do ERP E Concorrencia Da API

- A indisponibilidade da busca deixou de ser tratada como ausencia de produto:
  pedido de uma unica peca recebe HTTP 503; em pedido multiplo, cada peca
  conserva o status `error` e pode ser tentada novamente.
- A resposta, a telemetria e a captura de revisao distinguem `not_found` de
  erro. A captura armazena os resultados por item como uma acao interna,
  sem alterar o contrato HTTP de acoes para o cliente.
- Validacao LLM, busca PostgreSQL e gravacao da fila de revisao sao executadas
  fora do event loop. Ha limite configuravel de duas inferencias e quatro
  buscas simultaneas; LLM usa `LLM_TIMEOUT_MS` e a consulta usa
  `ERP_SEARCH_TIMEOUT_MS`, inclusive como `statement_timeout` no PostgreSQL.
- O auditor da LLM foi isolado por requisicao. Regressao focada confirmou que
  uma inferencia lenta nao bloqueia `/health` nem outra conversa deterministica.

## Operacao Verificada Em 21/09/2026

- A VPS acessa o ERP quente pelo backend `erp_postgres`; conectividade,
  autorizacao e objetos v2 foram conferidos. O snapshot local v2 serve para
  contingencia e reproducao.
- Checklist de deploy e fluxo sem GPU foram verificados. A proxima validacao
  operacional e a beta pelo canal real, com Redis e avaliacao comercial humana.

## Protecao Administrativa E Prontidao Preparadas Em 21/09/2026

- Em producao, a API falha na inicializacao sem `REVIEW_API_KEY` e
  `RESPOND_GATEWAY_API_KEY`. A chave de revisao protege `/review/*`; a chave
  de gateway e exigida quando `/respond` recebe historico ou estado do cliente.
- O `docker-comm` encaminha a chave de gateway em
  `X-Agent-Gateway-Key`. Entradas da API limitam texto, historico, itens e
  candidatos para impedir carga arbitraria do estado conversacional.
- `/health` continua leve e local ao processo. `/ready` verifica catalogo, ERP
  habilitado e inferencia, retornando `503` e `degraded` quando uma dependencia
  configurada nao estiver disponivel. As regressões foram adicionadas e ainda
  aguardam a rodada de testes da Prioridade 0.

## Endurecimento De Portas Preparado Em 21/09/2026

- A inspeção da VPS encontrou Redis (`6379`), catalogo (`5433`), Ollama
  (`11434`), agente (`8001`) e Streamlit (`8501`) publicados antes da mudanca.
  O Nginx ja atende o chat por `127.0.0.1:8501`, e o `docker-comm` usa
  `127.0.0.1:8002`.
- O Compose passou a limitar os servicos de manutencao ao loopback e removeu a
  publicacao do Redis. Falta aplicar na VPS e validar os listeners, o Nginx e
  a conexao de saida ao ERP. O UFW estava inativo; sua regra deve considerar
  tambem os outros projetos da maquina.

## Backup Manual Mantido Sob Revisao Em 21/09/2026

- A automacao de backup e restore foi adiada. O procedimento manual revisado
  continua cobrindo catalogo, regras, fila de revisao, dataset e estado
  conversacional necessario antes de qualquer deploy ou mudanca estrutural.
- A automacao volta ao backlog somente se a frequencia de operacao ou a beta
  mostrarem que o procedimento manual deixou de ser suficiente.
