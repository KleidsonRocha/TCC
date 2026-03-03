# docker-comm (Gateway) — Requisitos Mínimos para Produção Inicial (v0.1)

## 1. Objetivo
Implementar um **gateway/orquestrador** (docker-comm) em **Python + FastAPI** que:
- Receba mensagens de entrada (inicialmente via HTTP/Postman; futuramente via canais)
- Gerencie **sessão e contexto** de conversas
- Normalize a entrada para o **Contrato Técnico v1.0**
- Encaminhe requisições ao **docker-agent**
- Retorne a resposta do agente ao chamador/canal
- Aplique regras de negócio mínimas (branch default, formatação de actions, handoff)
- Registre logs para auditoria e troubleshooting

> Nota: este documento descreve a **entrega mínima operável** para iniciar testes ponta-a-ponta e permitir evolução segura.

---

## 2. Escopo da Entrega (v0.1)

### 2.1 Inclui
- API FastAPI containerizada (Docker)
- Endpoint de saúde (healthcheck)
- Endpoint de teste para simulação de conversas (Postman)
- Integração HTTP com docker-agent via `AGENT_URL`
- Redis para armazenamento de sessão (histórico curto)
- Logs estruturados com `trace_id` e métricas básicas de latência
- Aplicação de regras de negócio mínimas (ver Seção 5)

### 2.2 Não inclui (fora do v0.1)
- Integração com canal real (WhatsApp/Convert/Webchat)
- Idempotência completa baseada em `channel.message_id` (apenas estrutura preparada)
- Observabilidade avançada (Prometheus/OpenTelemetry)
- Persistência durável de conversas (PostgreSQL)
- Tratamento de anexos/áudio/imagem
- Painel de supervisão (fase supervisionada)
- Autenticação robusta (apenas token simples, se necessário)

---

## 3. Tecnologias e Dependências (v0.1)
- Python 3.11+
- FastAPI + Uvicorn
- httpx (chamada ao docker-agent)
- Redis (sessões)
- Docker + Docker Compose

---

## 4. Requisitos Funcionais (RF)

### RF-01 — Receber mensagem via endpoint de teste
O docker-comm deve oferecer um endpoint para envio de mensagens via Postman (sem canal).

**Endpoint:**
- `POST /test/send`

**Request mínimo:**
- `text` (obrigatório)
- `conversation_id` (opcional: se ausente, gerar UUID)
- `branch_id` (opcional: default 1)

---

### RF-02 — Gerenciar sessão mínima por conversa
O docker-comm deve manter, por `conversation_id`, um histórico curto de mensagens:

- Últimas `N` mensagens (default `N=6`)
- Papéis `role`: `user` e `assistant`
- Apenas texto no v0.1

---

### RF-03 — Montar payload no formato do Contrato Técnico v1.0
O docker-comm deve converter o request do `/test/send` para o schema do contrato:

Campos mínimos obrigatórios a preencher:
- `schema_version = "1.0"`
- `trace_id` (UUID)
- `conversation_id`
- `channel.name = "generic"`
- `message.text`
- `context.last_messages` (do Redis)
- `runtime.locale = "pt-BR"`
- `runtime.timezone = "America/Sao_Paulo"`
- `business.branch_id` (com regra de default)

---

### RF-04 — Encaminhar requisição ao docker-agent
O docker-comm deve chamar:

- `POST {AGENT_URL}`

Regras:
- Timeout configurável (default 20s)
- Retries mínimos (ex.: 1 retry) apenas em falhas transitórias (timeout/502/503)

---

### RF-05 — Retornar resposta padronizada ao chamador
O docker-comm deve retornar para o Postman uma resposta simplificada contendo:

- `conversation_id`
- `trace_id`
- `reply` (texto)
- `actions` (lista)
- `handoff` (objeto)
- `confidence` (número)

---

### RF-06 — Persistir resposta do agente no histórico
Após receber a resposta do agente, o docker-comm deve:
- Adicionar a mensagem do usuário ao histórico
- Adicionar a resposta do agente ao histórico
- Manter no máximo `N` mensagens

---

### RF-07 — Logs e rastreabilidade
O docker-comm deve registrar logs estruturados contendo:
- `trace_id`
- `conversation_id`
- endpoint acionado
- latência total
- status do agent (HTTP code)
- erros (stack/causa resumida)

---

## 5. Regras de Negócio Estruturadas (RB)

### RB-01 — Branch (Filial) obrigatório com default
- `business.branch_id` **sempre deve existir** no payload enviado ao agent
- Se `branch_id` não for informado na entrada:
  - aplicar `DEFAULT_BRANCH_ID = 1`
- Se `branch_id` informado for inválido (ex.: <=0, não numérico):
  - aplicar default 1 e registrar log de correção

---

### RB-02 — Contrato de actions deve ser preservado
- O docker-comm **não deve alterar** a estrutura de `actions`
- Se o canal (no futuro) não suportar botões:
  - a conversão de actions para texto será responsabilidade de um “adapter de canal”
  - no v0.1, apenas retornar `actions` no response

---

### RB-03 — Handoff deve ser respeitado
- Se o agent retornar `handoff.required = true`, o docker-comm deve:
  - retornar este campo ao chamador integralmente
  - registrar log com `handoff.reason`
- No v0.1 não há integração com humano, então:
  - o docker-comm não executa handoff, apenas sinaliza

---

### RB-04 — Mensagens vazias ou inválidas
- Se `text` estiver vazio/whitespace:
  - responder 400
  - payload não deve ser enviado ao agent
  - logar ocorrência com `trace_id`

---

### RB-05 — Latência e timeout
- Se a chamada ao agent exceder timeout:
  - responder 504 ao chamador
  - **não** atualizar histórico com resposta do agent
  - registrar log do timeout

---

### RB-06 — Falha do agent (5xx / indisponível)
- Se o agent falhar (5xx) ou estiver fora:
  - responder 502 ao chamador com mensagem padrão
  - registrar log de falha
  - histórico deve registrar apenas a mensagem do usuário (opcional) com flag de falha

Mensagem padrão sugerida (v0.1):
> "No momento não consegui processar sua solicitação. Tente novamente em instantes."

---

### RB-07 — Limite de histórico (context window)
- O docker-comm deve manter no máximo `HISTORY_LIMIT` mensagens por conversa
- O histórico deve ser “rolante” (descarta as mais antigas)

---

## 6. Requisitos Não-Funcionais (RNF)

### RNF-01 — Containerização
- O docker-comm deve rodar via Docker
- Deve existir `Dockerfile` e `docker-compose.yml` mínimo (comm + redis)

### RNF-02 — Configuração por ambiente
- URLs, limites e defaults via variáveis de ambiente:
  - `AGENT_URL` (obrigatória)
  - `REDIS_URL` (obrigatória)
  - `DEFAULT_BRANCH_ID` (opcional)
  - `HISTORY_LIMIT` (opcional)
  - `AGENT_TIMEOUT_SECONDS` (opcional)

### RNF-03 — Segurança mínima (produção inicial)
- O endpoint `/test/send` deve poder ser desativado via flag (ex.: `ENABLE_TEST_ENDPOINT=false`)
- Deve ser possível proteger endpoints com um token simples (ex.: header `X-API-Key`) — opcional no v0.1, mas recomendado para qualquer exposição pública

### RNF-04 — Resiliência
- Falhas do agent não devem derrubar o comm
- Comm deve responder com erro controlado e logado

---

## 7. Interfaces (Endpoints)

### 7.1 GET /health
**Response 200**
```json
{ "status": "ok" }

## 7.2 POST /test/send

### Request

```json
{
  "conversation_id": "conv-001",
  "text": "Preciso de bandeja da EcoSport 2008",
  "branch_id": 1
}
```

### Response (exemplo)

```json
{
  "conversation_id": "conv-001",
  "trace_id": "uuid",
  "reply": "Encontrei 2 opções. Você sabe se é 1.6 ou 2.0?",
  "actions": [
    {
      "type": "request_info",
      "key": "engine",
      "prompt": "Qual motorização?",
      "options": ["1.6", "2.0", "Não sei"]
    }
  ],
  "handoff": { "required": false, "reason": null },
  "confidence": 0.82
}
```

---

## 8. Critérios de Aceite (Definition of Done)

### CA-01 — Infraestrutura
- `docker-compose up` sobe `docker-comm` + `redis`
- `GET /health` retorna `200`

### CA-02 — Endpoint principal
- `POST /test/send`:
  - aceita texto
  - gera `trace_id`
  - gera `conversation_id` quando não informado

### CA-03 — Integração com Agent
- Comm chama `AGENT_URL`
- Retorna:
  - `reply`
  - `actions`
  - `handoff`
  - `confidence`

### CA-04 — Persistência de contexto
- Histórico armazenado no Redis
- Histórico reutilizado em mensagens subsequentes da mesma conversa

### CA-05 — Observabilidade
- Logs devem registrar:
  - `trace_id`
  - latência
  - status do agent

### CA-06 — Regra de filial (branch)
- `DEFAULT_BRANCH_ID` aplicado quando:
  - ausente
  - inválido

---

## 9. Entregáveis do v0.1

### Documentação
- `README.md` com instruções de execução

### Infraestrutura
- `Dockerfile` do `docker-comm`
- `docker-compose.yml` (comm + redis)

### Código (FastAPI)
- `main.py` — rotas
- `schemas.py` — modelos Pydantic
- `session_store.py` — sessão Redis
- `agent_client.py` — cliente HTTP (`httpx`)

### Configuração
- `.env.example` com variáveis necessárias

---

## 10. Próximas Evoluções (v0.2+)

### EV-01 — Idempotência
- Idempotência por `channel.message_id`

### EV-02 — Webhooks
- Endpoint `/webhook/inbound` genérico para canais

### EV-03 — Auditoria persistente
- Persistência durável em PostgreSQL

### EV-04 — Abstração de canal
- Conversão de `actions` para UX específica por canal

### EV-05 — Contexto resumido
- Implementação de `context.summary` (resumo automático)

