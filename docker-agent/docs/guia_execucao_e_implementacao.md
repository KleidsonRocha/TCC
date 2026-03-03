# Guia de Execucao e Implementacao - docker-agent (v0.1)

Este documento descreve:
- Como rodar o `docker-agent` em localhost (Python + Uvicorn)
- Como rodar o `docker-agent` em Docker Compose
- Como integrar com o `docker-comm` no endpoint `POST /respond`
- O que foi implementado no projeto e quais tecnologias foram usadas

## 1. Visao Geral

O `docker-agent` e um servico FastAPI que:
- Recebe requisicoes no contrato tecnico v1.0 em `POST /respond`
- Valida `schema_version` e `message.text`
- Executa tool calling minimo com `search_parts` (mock)
- Aplica regras de decisao para ambiguidade, match unico e sem match
- Retorna resposta estruturada com `reply`, `actions`, `handoff`, `confidence` e `tool_trace`
- Registra logs estruturados com `trace_id` e `conversation_id`

## 2. Matriz de Configuracao de Integracao

Use a combinacao correta de URL conforme onde cada servico esta rodando.

### Cenario A: `docker-agent` local e `docker-comm` local
- Agent em localhost: `http://localhost:8001/respond`
- No `docker-comm/.env`: `AGENT_URL=http://localhost:8001/respond`

### Cenario B: `docker-agent` em compose e `docker-comm` em compose
- Ambos na rede Docker compartilhada `tcc-integration`
- No `docker-comm/.env`: `AGENT_URL=http://docker-agent:8001/respond`

### Cenario C: `docker-agent` em compose e `docker-comm` local
- Agent publicado no host em `8001`
- No `docker-comm/.env`: `AGENT_URL=http://localhost:8001/respond`

## 3. Execucao Local (localhost com Uvicorn)

### 3.1 Pre-requisitos
- Python 3.11+

### 3.2 Passos
1. Criar e ativar ambiente virtual:
```cmd
cd D:\TCC\docker-agent
py -3.12 -m venv .venvpy
call .venvpy\Scripts\activate.bat
```
2. Instalar dependencias:
```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```
3. Ajustar variaveis em `.env` (ou exportar no shell):
```env
APP_ENV=dev
LOG_LEVEL=INFO
AGENT_PORT=8001
DEFAULT_LOCALE=pt-BR
DEFAULT_TIMEZONE=America/Sao_Paulo
```
4. Subir API:
```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 3.3 Teste rapido
1. Health:
```http
GET http://localhost:8001/health
```
2. Respond:
```http
POST http://localhost:8001/respond
Content-Type: application/json

{
  "schema_version": "1.0",
  "trace_id": "trace-001",
  "conversation_id": "generic:conv-001",
  "channel": { "name": "generic" },
  "message": { "text": "Preciso de bandeja da EcoSport 2008" },
  "context": { "last_messages": [] },
  "runtime": { "locale": "pt-BR", "timezone": "America/Sao_Paulo" },
  "business": { "branch_id": 1 }
}
```

## 4. Execucao via Docker Compose

### 4.1 Pre-requisitos
- Docker Desktop com engine ativo

### 4.2 Passos
1. Garantir arquivo `.env` na raiz do `docker-agent`:
```cmd
cd D:\TCC\docker-agent
copy .env.example .env
```
2. Subir stack:
```cmd
docker compose up -d --build
```
3. Validar:
```cmd
docker compose ps
docker compose logs -f docker-agent
```

### 4.3 Testes
- `GET http://localhost:8001/health`
- `POST http://localhost:8001/respond`

## 5. Integracao com docker-comm

Para o fluxo ponta a ponta funcionar:
1. Suba o `docker-agent` e o `docker-comm`.
2. Garanta no `docker-comm/.env`:
```env
AGENT_URL=http://docker-agent:8001/respond
```
3. Com ambos em Docker, confirme que os dois stacks usam a rede `tcc-integration`.
4. Teste pelo comm:
```http
POST http://localhost:8000/test/send
Content-Type: application/json

{
  "conversation_id": "conv-001",
  "text": "Preciso de bandeja da EcoSport 2008",
  "branch_id": 1
}
```

## 6. O que foi implementado

## 6.1 Arquitetura e organizacao de codigo

Foi implementada arquitetura em camadas:
- `app/api`: rotas, schemas e dependencias de API
- `app/core/domain`: modelos, erros e regras de validacao
- `app/core/usecases`: fluxo principal `ProcessAgentRequestUseCase`
- `app/core/ports`: contrato da tool (`ToolsPort`)
- `app/infra`: adaptadores concretos (`tools_mock`, logger JSON)
- `app/main.py`: composicao da aplicacao e ciclo de vida

## 6.2 Endpoints

- `GET /health`: retorna `{ "status": "ok" }`
- `POST /respond`: recebe contrato v1.0 e retorna:
  - `schema_version`
  - `trace_id`
  - `conversation_id`
  - `reply.text`
  - `actions`
  - `handoff`
  - `confidence`
  - `tool_trace`

## 6.3 Regras de negocio implementadas

- `RB-A01`: se `schema_version != "1.0"`, retorna `400`
- `RB-A02`: se `message.text` vazio/whitespace, retorna `400`
- `RB-A03`: qualquer texto valido chama `search_parts(query, branch_id)`
- `RB-A04`: sem resultados retorna `handoff.required=true` e `reason="no_match"`
- `RB-A05`: multiplos resultados retornam `request_info` e `show_items`
- `RB-A06`: resultado unico retorna resposta direta com item encontrado
- `RB-A07`: sempre retorna `tool_trace.used_tools` e `tool_trace.latency_ms`

## 6.4 Tool mock implementada

`search_parts(query, branch_id)`:
- Contem `bandeja` -> retorna 2 itens
- Contem `filtro de oleo` -> retorna 1 item
- Caso contrario -> retorna lista vazia

Item minimo retornado:
- `item_id`
- `title`
- `score` (0..1)

## 6.5 Logs e rastreabilidade

Logs estruturados em JSON com:
- `trace_id`
- `conversation_id`
- `latency_ms`
- `used_tools`
- status da requisicao

Eventos principais:
- `service_started`
- `tool_search_parts_finished`
- `respond_processed`
- `respond_unhandled_error`

## 6.6 Configuracao por ambiente

Variaveis suportadas:
- `APP_ENV`
- `LOG_LEVEL`
- `AGENT_PORT`
- `DEFAULT_LOCALE`
- `DEFAULT_TIMEZONE`

## 6.7 Testes automatizados incluidos

Pasta `tests/` com testes iniciais:
- `test_rules.py`: validacao de schema, texto e comportamento da tool mock
- `test_respond.py`: cobrindo health, cenarios de busca e erros `400`

## 7. Comandos uteis

### 7.1 Subir stack
```cmd
docker compose up -d --build
```

### 7.2 Derrubar stack
```cmd
docker compose down
```

### 7.3 Rodar testes
```cmd
python -m pytest -q
```

## 8. Erros comuns e solucao

### 8.1 `env file ...\\.env not found`
Causa:
- `docker-compose.yml` tentando carregar `.env` inexistente
Solucao:
- Criar `.env` com base no `.env.example`

### 8.2 `502 Bad Gateway` no `/test/send` do comm e sem log no agent
Causa:
- `docker-comm` nao consegue resolver/alcancar `docker-agent`
Solucao:
- Confirmar `AGENT_URL=http://docker-agent:8001/respond` no comm
- Confirmar ambos os stacks na rede `tcc-integration`

### 8.3 `400` com detalhe de `schema_version`
Causa:
- Payload enviado ao agent com versao diferente de `1.0`
Solucao:
- Corrigir para `schema_version: "1.0"`

### 8.4 `400` com detalhe de `message.text`
Causa:
- Texto vazio ou apenas espacos
Solucao:
- Enviar mensagem valida em `message.text`
