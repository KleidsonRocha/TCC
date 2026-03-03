# Esqueleto — docker-agent (v0.1)

## 1) Objetivo
Implementar o **docker-agent** em **Python + FastAPI** que:
- Receba requisições do `docker-comm` via HTTP
- Processe mensagens conforme **Contrato Técnico v1.0** (mínimo)
- Execute **tool calling mínimo** (mock no v0.1)
- Retorne resposta estruturada para o `docker-comm`

> Compatibilidade obrigatória com o `docker-comm`:
> `AGENT_URL=http://docker-agent:8001/respond`

---

## 2) Escopo da Entrega (v0.1)

### Inclui
- API FastAPI containerizada
- Endpoints:
  - `GET /health`
  - `POST /respond`
- Validação mínima do request (schema_version e texto)
- Tool mock `search_parts(query, branch_id)`
- Regras de decisão:
  - múltiplos resultados → `request_info` (+ opcional `show_items`)
  - 1 resultado → resposta direta
  - 0 resultados → `handoff.required = true`
- `tool_trace` com tools e latência
- Logs estruturados com `trace_id` e `conversation_id`

### Não inclui
- LLM real
- Fine-tuning
- Integrações com DB/ERP
- Elastic/OpenSearch
- RAG

---

## 3) Contrato Mínimo Aceito (Request v1.0)

### Campos obrigatórios (v0.1)
- `schema_version` (deve ser `"1.0"`)
- `trace_id`
- `conversation_id`
- `message.text`
- `business.branch_id`

### Campos opcionais
- `channel.name`
- `context.last_messages`
- `runtime.locale`
- `runtime.timezone`

---

## 4) Contrato Mínimo Retornado (Response v1.0)

### Campos obrigatórios
- `schema_version`
- `trace_id`
- `reply.text`
- `actions` (lista, pode ser vazia)
- `handoff.required`
- `confidence` (0..1)
- `tool_trace.used_tools`
- `tool_trace.latency_ms`

---

## 5) Regras de Negócio (RB) — docker-agent v0.1

### RB-A01 — Versão de schema
- Se `schema_version != "1.0"` → responder **400** (erro controlado)

### RB-A02 — Mensagem vazia
- Se `message.text` vazio/whitespace → responder **400**

### RB-A03 — Busca de peça (tool mock)
- No v0.1, qualquer `message.text` não vazio é tratado como consulta de peça
- Deve chamar `search_parts(query, branch_id)`

### RB-A04 — Sem resultados
- Se `search_parts` retornar 0 itens:
  - `handoff.required = true`
  - `handoff.reason = "no_match"`
  - `reply.text` orienta “não encontrei / preciso de detalhes / posso transferir…”

### RB-A05 — Ambiguidade
- Se `search_parts` retornar 2+ itens:
  - retornar `actions` com `request_info`
  - opcional: incluir `show_items` com candidatos

### RB-A06 — Resultado único
- Se `search_parts` retornar 1 item:
  - retornar resposta direta com identificação do item
  - sugerir próxima pergunta útil (motor/lado/versão)
  - `handoff.required = false`

### RB-A07 — tool_trace obrigatório
- Sempre retornar `tool_trace` com:
  - `used_tools` (no v0.1: sempre inclui `"search_parts"`)
  - `latency_ms` total do processamento

---

## 6) Tool mock (v0.1)

### search_parts
Assinatura:
- `search_parts(query: str, branch_id: int) -> list[Item]`

Comportamento mínimo sugerido:
- Se query contém `"bandeja"` → retornar **2 itens**
- Se query contém `"filtro de óleo"` → retornar **1 item**
- Caso contrário → retornar **0 itens**

Item mínimo:
- `item_id` (string)
- `title` (string)
- `score` (float 0..1)

---

## 7) Interfaces (Endpoints)

### 7.1 GET /health
**Response 200**
```json
{ "status": "ok" }

7.2 POST /respond

Recebe request do contrato v1.0 (mínimo) e retorna response do contrato v1.0.

8) Critérios de Aceite (Definition of Done)
CA-A01 — Infra

docker compose up sobe docker-agent

GET /health retorna 200

CA-A02 — Endpoint principal

POST /respond valida schema e retorna response no formato esperado

CA-A03 — Casos mínimos

Consulta com "bandeja" → múltiplos resultados → request_info + tool_trace

Consulta com "filtro de óleo" → resultado único → resposta direta + tool_trace

Consulta genérica sem match → handoff.required=true + reason="no_match"

CA-A04 — Logs

Logs com trace_id, conversation_id, latência e tools usadas

9) Estrutura do Projeto (estrutura.md)
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
10) docker-compose (compatível com o docker-comm)

Requisito:

service name deve ser docker-agent

expor porta 8001

rota deve existir em POST /respond

Exemplo mínimo:

services:
  docker-agent:
    build: .
    container_name: docker-agent
    ports:
      - "8001:8001"
    environment:
      - LOG_LEVEL=INFO
      - DEFAULT_LOCALE=pt-BR
      - DEFAULT_TIMEZONE=America/Sao_Paulo