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

## Subir com Docker

```bash
docker compose up --build
```

API exposta em `http://localhost:8000`.

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
  "reply": "Encontrei 2 opcoes. Voce sabe se e 1.6 ou 2.0?",
  "actions": [],
  "handoff": { "required": false, "reason": null },
  "confidence": 0.82
}
```

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
- Retry minimo em timeout/502/503 para chamada ao agent
- Timeout controlado para agent (retorno 504)
- Falha do agent (5xx/indisponivel) retorna 502 com mensagem padrao
- Persistencia de historico curto no Redis (`HISTORY_LIMIT`)
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
