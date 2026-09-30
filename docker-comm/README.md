# docker-comm (v0.1)

Gateway/orquestrador em FastAPI para receber mensagens, montar payload no contrato tecnico v1.0, chamar o `docker-agent` e manter contexto curto por conversa no Redis.

## Requisitos

- Docker e Docker Compose
- Ou Python 3.11+ para execucao local

## Estrutura

```
docker-comm/
  app/
    main.py
    api/
      routes/
        health.py
        test_send.py
      deps.py
      schemas.py
    core/
      usecases/
        process_inbound_message.py
      domain/
        models.py
        errors.py
        rules.py
      ports/
        session_store.py
        agent_client.py
        audit_repo.py
    infra/
      session_store_redis.py
      agent_client_http.py
      logger.py
    config.py
  tests/
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
```

## Configuracao

1. Copie `.env.example` para `.env`
2. Ajuste principalmente:
   - `AGENT_URL` (obrigatoria)
   - `REDIS_URL` (obrigatoria)
   - `AGENT_GATEWAY_API_KEY` (obrigatoria quando o `docker-agent` estiver em
     producao; deve ter o mesmo valor de `RESPOND_GATEWAY_API_KEY`)

## Subir com Docker

```bash
docker compose up --build
```

Por padrao, a API e exposta em `http://localhost:8000`.
Interface Streamlit exposta em `http://localhost:8501`.

`COMM_BIND_HOST` e `COMM_PORT` controlam somente a porta publicada no host;
a comunicacao entre containers continua usando `http://docker-comm:8000`.
Em uma VPS com proxy reverso, use `COMM_BIND_HOST=127.0.0.1` e uma porta local,
como `COMM_PORT=8002`, no `.env` nao versionado.

## Endpoints

### Health

`GET /health`

Resposta:

```json
{ "status": "ok" }
```

### Teste de envio

`POST /test/send`

Request:

```json
{
  "source": "generic",
  "conversation_id": "conv-001",
  "text": "Preciso de bandeja da EcoSport 2008",
  "branch_id": 1
}
```

Response:

```json
{
  "conversation_id": "conv-001",
  "trace_id": "uuid",
  "status": "completed",
  "stage": "more_info",
  "reply": "Encontrei 2 opcoes. Voce sabe se e 1.6 ou 2.0?",
  "actions": [{ "type": "request_info", "key": "engine", "prompt": "Voce sabe se e 1.6 ou 2.0?" }],
  "items": [],
  "items_text": "",
  "handoff": { "required": false, "reason": null },
  "confidence": 0.82
}
```

O mesmo `POST /test/send` tambem recupera uma solicitacao em andamento ou
concluida. Use o mesmo `source`, `conversation_id`, `branch_id` e `text` em cada
repeticao. O `conversation_id` precisa vir da sala da Convert e permanecer
estavel; se for omitido, a API gera um novo ID e nao consegue reconhecer a
repeticao. A chave inclui o texto com espacos e maiusculas normalizados.

O servidor inicia uma unica chamada ao agent e espera ate `TURN_WAIT_SECONDS`
(35 s por padrao). Se ainda nao houver resposta, devolve HTTP 200:

```json
{
  "conversation_id": "conv-001",
  "trace_id": "uuid-da-primeira-chamada",
  "status": "processing",
  "stage": null,
  "reply": "",
  "actions": [],
  "items": [],
  "items_text": "",
  "handoff": { "required": false, "reason": null },
  "confidence": 0.0
}
```

O processamento continua apos a resposta HTTP ou desconexao do cliente. Um
POST repetido aguarda novamente ate 35 s; se o resultado ja estiver pronto,
retorna a resposta original imediatamente, com o mesmo `trace_id`. O resultado
fica disponivel por `TURN_RESULT_TTL_SECONDS` (300 s por padrao) apos a
conclusao. O bloqueio de processamento usa uma concessao renovada no Redis;
se o processo morrer, a concessao expira e uma nova chamada pode reiniciar o
trabalho. Falhas do agent retornam o mesmo erro HTTP armazenado durante a
janela de retencao.

Na Convert, trate `status=processing` antes de enviar `reply`: aguarde e repita
o POST com os mesmos dados. Envie `reply` apenas quando `status=completed`.
Um timeout de 40 s no bloco HTTP pode continuar como caminho de recuperacao.
Sem um identificador proprio da mensagem, dois textos iguais na mesma sala e
filial enviados dentro da janela de 5 minutos podem compartilhar o resultado.

### Etapa conversacional para a Convert

`status` informa se o processamento terminou. `stage` informa o proximo passo
somente quando `status=completed`. Em `processing`, `stage=null`, `reply` e
`items_text` vazios. A precedencia para um resultado concluido e:

1. `transfer_to_human` se `handoff.required=true`, mesmo com outras acoes;
2. `more_info` se houver `request_info`, inclusive junto com `show_items`;
3. `mostrar_produtos` se houver `show_items` sem os casos anteriores;
4. `fallback` quando nao houver nenhuma dessas acoes.

O retorno preserva `actions` integralmente. `items` reune os objetos das acoes
`show_items`, com `item_id`, `title` e `score` quando fornecidos pelo agent.
`items_text` apresenta os codigos e descricoes em linhas numeradas, pronto
para um bloco de mensagem simples. Exemplo:

```json
{
  "status": "completed",
  "stage": "mostrar_produtos",
  "reply": "Encontrei 2 opcoes. Preco e estoque precisam ser confirmados.",
  "actions": [{"type": "show_items", "items": [
    {"item_id": "ABC123", "title": "Pastilha de freio dianteira", "score": 0.91},
    {"item_id": "DEF456", "title": "Pastilha de freio dianteira", "score": 0.87}
  ]}],
  "items": [
    {"item_id": "ABC123", "title": "Pastilha de freio dianteira", "score": 0.91},
    {"item_id": "DEF456", "title": "Pastilha de freio dianteira", "score": 0.87}
  ],
  "items_text": "1. ABC123 - Pastilha de freio dianteira\n2. DEF456 - Pastilha de freio dianteira"
}
```

No bloco HTTP da Convert, mapeie `$.status` para `$statusProcesso`, `$.stage`
para `$estado_ia`, `$.reply` para `$resposta_ia` e `$.items_text` para uma
variavel como `$itens_ia`. Se a interface permitir acessar listas, `$.items`
e `$.actions` continuam disponiveis; por exemplo `$.items[0].item_id`.

Roteamento sugerido:

1. `processing` -> aguardar 30 s -> repetir o mesmo POST, sem enviar mensagem;
2. `completed` -> enviar `$resposta_ia` -> validar `$estado_ia`;
3. `more_info` -> se `$itens_ia` nao estiver vazio, apresentar os candidatos
   para escolha; depois aguardar nova mensagem do cliente e iniciar novo turno
   com o mesmo `conversation_id` e o novo `text`;
4. `mostrar_produtos` -> enviar `$itens_ia` se houver itens e seguir o fluxo de
   apresentacao, sem repetir a requisicao anterior;
5. `transfer_to_human` -> transferir para o departamento humano, sem aguardar
   outra mensagem para o agent;
6. `fallback` -> caminho de contingencia, como transferencia humana.

O caminho `Falhou` do HTTP e a excecao das condicoes tambem devem seguir a
contingencia. O timeout de 40 s pode aguardar e repetir o mesmo POST. O
`conversation_id` deve ser preenchido com o `room_id` da Convert e permanecer
igual durante a conversa; na repeticao do mesmo turno, `text` tambem deve ser
identico. A apresentacao de `items_text` nao confirma preco, estoque ou
compatibilidade alem do que o agent informou.

## Interface Streamlit

O compose sobe o servico `docker-comm-ui`, que chama o `docker-comm` em vez de
chamar o `docker-agent` diretamente.

```bash
docker compose up --build
```

Acesse:

```text
http://localhost:8501
```

A UI possui:

- aba `Conversa` para abrir uma conversa, enviar mensagens e receber respostas;
- aba `Uso` com requisicoes da sessao, latencia, confianca, handoff, acoes e ultima resposta bruta;
- aba `Revisao de IA` para avaliar turnos capturados, vendo toda a conversa como contexto;
- painel lateral para ajustar `Comm API`, origem, filial e `conversation_id`.

Na revisao, salvar ou descartar o ultimo turno pendente remove a conversa da fila
`Pendentes`. Ela continua consultavel em `Concluidas`, onde a interface informa
que a conversa ja foi avaliada. Uma revisao nao promove automaticamente o turno
para o dataset de fine-tuning.

Pedidos com varias pecas podem ser divididos em cartoes com criterios, decisao e
pendencias proprios. Um turno revisado ou descartado tambem pode ser reaberto pela
interface; a revisao anterior permanece no historico de auditoria.

Variaveis relevantes:

```env
COMM_API_URL=http://docker-comm:8000
REVIEW_API_URL=http://docker-agent:8001
REVIEW_API_KEY=
REVIEWED_BY=streamlit-reviewer
STREAMLIT_PORT=8501
STREAMLIT_SOURCE=webchat
COMM_BIND_HOST=0.0.0.0
COMM_PORT=8000
```

Quando `API_KEY` estiver definido no `docker-comm`, a UI usa esse mesmo valor
como `COMM_API_KEY` no container.

## Controle de conversa por origem

- `source` e opcional (default `generic`)
- O `conversation_id` retornado na API permanece igual ao enviado pelo cliente
- Internamente, o comm usa `source:conversation_id` para:
  - chave de historico no Redis
  - `conversation_id` enviado ao agent
- Exemplo:
  - entrada: `source="whatsapp"` e `conversation_id="123"`
  - interno: `whatsapp:123`

## Comportamentos implementados

- Default de filial (`DEFAULT_BRANCH_ID`) quando `branch_id` vier ausente/invalido
- Validacao de `text` vazio retornando HTTP 400
- Namespacing interno de conversa por origem (`source:conversation_id`)
- Montagem do payload no contrato tecnico v1.0
- Retry minimo em falhas de conexao/502/503; chamadas expiradas nao sao reenviadas para evitar duplicar turnos ainda em processamento
- Timeout configuravel de 270 s para o agent, acima do limite de 240 s do Ollama
- Falha do agent (5xx/indisponivel) retorna 502 com mensagem padrao
- Persistencia de historico curto no Redis (`HISTORY_LIMIT`)
- Persistencia retrocompativel de `result_disambiguation` dentro do mesmo `ConversationState` e da mesma chave `conv:{conversation_id}:state`
- Logs estruturados com `trace_id`, `conversation_id`, latencia e status do agent
- Endpoint `/test/send` pode ser desativado via `ENABLE_TEST_ENDPOINT`
- Suporte opcional a `X-API-Key` quando `API_KEY` estiver definido

## Execucao local (sem Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

## Testes

```bash
pytest -q
```
