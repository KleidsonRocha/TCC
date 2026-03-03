# docker-agent (v0.1)

Servico FastAPI do agente especialista para receber chamadas do `docker-comm` em `POST /respond`, aplicar regras de negocio minimas e devolver resposta estruturada no contrato v1.0.

## Requisitos

- Docker e Docker Compose
- Ou Python 3.11+ para execucao local

## Estrutura

```text
docker-agent/
  app/
    main.py
    api/
      routes/
        health.py
        respond.py
      deps.py
      schemas/
        contract_v1.py
    core/
      usecases/
        process_agent_request.py
      domain/
        models.py
        errors.py
        rules.py
      ports/
        tools.py
    infra/
      tools_mock.py
      logger.py
    config.py
  tests/
    test_respond.py
    test_rules.py
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
  README.md
```

## Configuracao

1. Copie `.env.example` para `.env`
2. Ajuste as variaveis se necessario:
   - `LOG_LEVEL`
   - `AGENT_PORT`
   - `DEFAULT_LOCALE`
   - `DEFAULT_TIMEZONE`

## Subir com Docker

```bash
docker compose up --build
```

API exposta em `http://localhost:8001`.

## Endpoints

### Health

`GET /health`

Resposta:

```json
{ "status": "ok" }
```

### Respond

`POST /respond`

Request minimo:

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "conversation_id": "conv-001",
  "message": { "text": "Preciso de bandeja da EcoSport 2008" },
  "business": { "branch_id": 1 }
}
```

Response (exemplo):

```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "conversation_id": "conv-001",
  "reply": { "text": "Encontrei mais de uma opcao. Pode me confirmar a motorizacao?" },
  "actions": [
    {
      "type": "request_info",
      "key": "engine",
      "prompt": "Qual a motorizacao do veiculo?",
      "options": ["1.6", "2.0", "Nao sei"]
    }
  ],
  "handoff": { "required": false, "reason": null },
  "confidence": 0.82,
  "tool_trace": {
    "used_tools": ["search_parts"],
    "latency_ms": 12.4
  }
}
```

## Regras implementadas

- `schema_version` diferente de `1.0` retorna HTTP 400
- `message.text` vazio/whitespace retorna HTTP 400
- `search_parts` mock:
  - contem `bandeja` -> 2 itens (ambiguidade)
  - contem `filtro de oleo` -> 1 item
  - caso contrario -> 0 itens
- 0 itens -> `handoff.required=true` e `reason=no_match`
- 2+ itens -> `request_info` + `show_items`
- 1 item -> resposta direta com sugestao de proxima validacao
- `tool_trace` sempre inclui `search_parts` e latencia total
- logs estruturados com `trace_id`, `conversation_id`, status e latencia

## Execucao local (sem Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir . --port 8001
```

## Testes

```bash
pytest -q
```
