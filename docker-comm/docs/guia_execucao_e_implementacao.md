# Guia de Execucao e Implementacao - docker-comm (v0.1)

Este documento descreve:
- Como rodar o `docker-comm` em localhost (Python + Uvicorn)
- Como rodar o `docker-comm` em Docker Compose
- Como configurar `AGENT_URL` e `REDIS_URL` em cada cenario
- O que foi implementado no projeto e quais tecnologias foram usadas

## 1. Visao Geral

O `docker-comm` e um gateway/orquestrador em FastAPI que:
- Recebe mensagens em `POST /test/send`
- Monta o payload no contrato tecnico `schema_version = "1.0"`
- Consulta o `docker-agent` via HTTP
- Persiste contexto curto da conversa no Redis
- Faz namespacing interno de conversa por origem (`source:conversation_id`)
- Retorna resposta simplificada para o chamador
- Registra logs estruturados para rastreabilidade

## 2. Matriz de Configuracao (AGENT_URL e REDIS_URL)

Use a combinacao correta conforme onde cada servico esta rodando.

### Cenario A: `docker-comm` local (Uvicorn no Windows)
- Redis em container com porta publicada: `REDIS_URL=redis://localhost:6379/0`
- Agent local no host: `AGENT_URL=http://localhost:8001/respond`

### Cenario B: `docker-comm` em Docker Compose
- Redis no mesmo compose/rede: `REDIS_URL=redis://redis:6379/0`
- Agent no mesmo compose/rede: `AGENT_URL=http://docker-agent:8001/respond`

### Cenario C: `docker-comm` em Docker e agent no host
- Redis no compose: `REDIS_URL=redis://redis:6379/0`
- Agent no host (Windows): `AGENT_URL=http://host.docker.internal:8001/respond`

## 3. Execucao Local (localhost com Uvicorn)

### 3.1 Pre-requisitos
- Python 3.11+
- Docker Desktop ativo (para subir apenas o Redis, se desejar)

### 3.2 Passos
1. Criar e ativar ambiente virtual:
```cmd
cd D:\TCC\docker-comm
py -3.12 -m venv .venvpy
call .venvpy\Scripts\activate.bat
```
2. Instalar dependencias:
```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```
3. Ajustar `.env` para modo local:
```env
AGENT_URL=http://localhost:8001/respond
REDIS_URL=redis://localhost:6379/0
```
4. Subir Redis (se nao tiver local instalado):
```cmd
docker compose up -d redis
```
5. Subir API:
```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.3 Teste rapido
1. Health:
```http
GET http://localhost:8000/health
```
2. Send:
```http
POST http://localhost:8000/test/send
Content-Type: application/json

{
  "source": "generic",
  "conversation_id": "conv-001",
  "text": "Preciso de bandeja da EcoSport 2008",
  "branch_id": 1
}
```

## 4. Execucao via Docker Compose

### 4.1 Pre-requisitos
- Docker Desktop com engine ativo

### 4.2 Passos
1. Ajustar `.env` para modo compose:
```env
AGENT_URL=http://docker-agent:8001/respond
REDIS_URL=redis://redis:6379/0
```
2. Subir stack:
```cmd
cd D:\TCC\docker-comm
docker compose up -d --build
```
3. Validar:
```cmd
docker compose ps
docker compose logs -f docker-comm
```

### 4.3 Testes
- `GET http://localhost:8000/health`
- `POST http://localhost:8000/test/send`

## 5. O que foi implementado

## 5.1 Arquitetura e organizacao de codigo

Foi implementada arquitetura em camadas:
- `app/api`: rotas, schemas e dependencias de API
- `app/core/domain`: regras e modelos de dominio
- `app/core/usecases`: fluxo de negocio principal
- `app/core/ports`: contratos abstratos (session store e agent client)
- `app/infra`: adaptadores concretos (Redis, HTTP client e logger)
- `app/main.py`: composicao da aplicacao e ciclo de vida

## 5.2 Endpoints

- `GET /health`: retorna `{ "status": "ok" }`
- `POST /test/send`: recebe texto, opcionalmente conversa/filial, processa e retorna:
  - `source` (opcional, default `generic`)
  - `conversation_id`
  - `trace_id`
  - `reply`
  - `actions`
  - `handoff`
  - `confidence`

## 5.3 Controle de conversa por origem

Para evitar colisao de IDs entre plataformas, o comm separa contexto por origem.

- Entrada publica:
  - `source` (ex.: `whatsapp`, `webchat`, `generic`)
  - `conversation_id` (ID da plataforma integradora)
- Identificador interno:
  - `<source>:<conversation_id>`
- Uso do identificador interno:
  - chave de historico no Redis
  - `conversation_id` enviado ao `docker-agent`
- Resposta da API:
  - devolve `conversation_id` original (sem prefixo interno)

Exemplo:
- entrada: `source = "whatsapp"` e `conversation_id = "5511999999999"`
- interno: `whatsapp:5511999999999`

## 5.4 Regras de negocio implementadas

- `RB-01`: `branch_id` obrigatorio no payload final com default `DEFAULT_BRANCH_ID=1`
- `RB-02`: `actions` preservadas sem transformacao
- `RB-03`: `handoff` repassado integralmente e logado quando `required=true`
- `RB-04`: texto vazio retorna `400`
- `RB-05`: timeout de agent retorna `504`
- `RB-06`: falha/indisponibilidade do agent retorna `502` com mensagem padrao
- `RB-07`: historico limitado por `HISTORY_LIMIT` (janela rolante)

## 5.5 Persistencia de contexto

O historico por `source:conversation_id` e salvo no Redis:
- Armazena mensagens `user` e `assistant`
- Mantem apenas as ultimas `N` mensagens (`HISTORY_LIMIT`)
- Usa TTL configuravel (`SESSION_TTL_SECONDS`)

## 5.6 Integracao com docker-agent

Cliente HTTP implementado com `httpx`:
- Chamada `POST` para `AGENT_URL`
- Timeout configuravel (`AGENT_TIMEOUT_SECONDS`)
- Retry minimo para falhas transitorias (timeout, 502, 503)
- Validacao/normalizacao da resposta do agent

## 5.7 Logs e rastreabilidade

Logs estruturados em JSON com:
- `trace_id`
- `conversation_id`
- `internal_conversation_id`
- `source`
- endpoint
- latencia total (`latency_ms`)
- status HTTP do agent quando houver
- erros com stack trace resumida

## 5.8 Configuracao por ambiente

Variaveis suportadas:
- `AGENT_URL` (obrigatoria)
- `REDIS_URL` (obrigatoria)
- `DEFAULT_BRANCH_ID`
- `HISTORY_LIMIT`
- `SESSION_TTL_SECONDS`
- `AGENT_TIMEOUT_SECONDS`
- `AGENT_RETRY_COUNT`
- `ENABLE_TEST_ENDPOINT`
- `API_KEY` (opcional)
- `LOG_LEVEL`

## 5.9 Seguranca minima

- Possibilidade de desativar `/test/send` com `ENABLE_TEST_ENDPOINT=false`
- Protecao opcional por `X-API-Key` quando `API_KEY` estiver definido

## 5.10 Testes automatizados incluidos

Pasta `tests/` com testes iniciais:
- `test_rules.py`: valida regras de texto e branch
- `test_test_send_endpoint.py`: valida comportamento basico do endpoint

## 6. Comandos uteis

### 6.1 Subir somente Redis
```cmd
docker compose up -d redis
```

### 6.2 Derrubar stack
```cmd
docker compose down
```

### 6.3 Rodar testes
```cmd
python -m pytest -q
```

## 7. Erros comuns e solucao

### 7.1 `Error 11001 connecting to redis:6379`
Causa:
- `docker-comm` local tentando resolver host `redis` (nome interno de container)
Solucao:
- Em execucao local, usar `REDIS_URL=redis://localhost:6379/0`

### 7.2 `502 Bad Gateway` no `/test/send`
Causa:
- `docker-agent` indisponivel ou URL incorreta
Solucao:
- Verificar se o agent esta no ar e se `AGENT_URL` esta correto para o cenario

### 7.3 `docker compose` sem conectar ao engine
Causa:
- Docker Desktop/daemon nao iniciado
Solucao:
- Abrir Docker Desktop e aguardar `Engine running`
