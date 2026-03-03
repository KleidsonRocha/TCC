# docker-agent (Agente) — Requisitos Mínimos + Estrutura (v0.1)

## 1. Objetivo
Implementar o **docker-agent** em **Python + FastAPI** que:
- Receba requisições do `docker-comm` no formato do **Contrato Técnico v1.0**.
- Execute um fluxo mínimo de "agente especialista" (sem fine-tuning no v0.1).
- Realize **tool calling mínimo** (inicialmente com tools mock).
- Retorne resposta estruturada com:
  - `reply.text`
  - `actions` (suporte a opções/botões)
  - `handoff`
  - `confidence`
  - `tool_trace`
- Registre logs estruturados (traceabilidade ponta a ponta).

> Nota: no v0.1 o foco é validar o **fluxo completo comm → agent → comm** com estabilidade e contrato, antes de integrar banco/ERP/Elastic/LLM real.

---

## 2. Endpoint e Compatibilidade com o docker-comm

### 2.1 Endpoint obrigatório
- `POST /respond`

### 2.2 Porta e host no Docker
- O container deve expor `8001` internamente e para a rede do compose.

### 2.3 Compatibilidade com a env do docker-comm
O docker-comm está configurado para:
- `AGENT_URL=http://docker-agent:8001/respond`

Logo, no docker-compose:
- o **service name** deve ser `docker-agent`
- o agent deve escutar em `0.0.0.0:8001`
- deve existir rota `POST /respond`

---

## 3. Escopo da Entrega (v0.1)

### 3.1 Inclui
- API FastAPI containerizada (Docker).
- Endpoint `/respond` com schema do contrato v1.0 (mínimo necessário).
- Use case principal de processamento (`ProcessAgentRequest`).
- Tool mock: `search_parts` (simulador).
- Regras de decisão (ambiguidade, sem resultados, pedir dados).
- Logs estruturados (JSON) com `trace_id`, `conversation_id`.
- `docker-compose.yml` (agent standalone) e compatível para integração com comm.

### 3.2 Não inclui (fora do v0.1)
- Integração com Postgres/ERP real.
- Elastic/OpenSearch.
- Vetor/RAG.
- Fine-tuning / LoRA / QLoRA.
- Autorização/autenticação avançada.
- Idempotência (poderá ser adicionada no comm).

---

## 4. Contrato Técnico Aceito pelo docker-agent (mínimo)

### 4.1 Request (mínimo esperado)
Campos obrigatórios para o v0.1:
- `schema_version`
- `trace_id`
- `conversation_id`
- `message.text`
- `business.branch_id`

Campos opcionais:
- `runtime.locale` (default `pt-BR`)
- `runtime.timezone` (default `America/Sao_Paulo`)
- `context.last_messages`

Exemplo:
```json
{
  "schema_version": "1.0",
  "trace_id": "uuid",
  "conversation_id": "conv-001",
  "channel": { "name": "generic" },
  "message": { "text": "Preciso de bandeja da EcoSport 2008" },
  "context": { "last_messages": [] },
  "runtime": { "locale": "pt-BR", "timezone": "America/Sao_Paulo" },
  "business": { "branch_id": 1 }
}
```

### 4.2 Response (mínimo esperado)
Campos de retorno obrigatórios:
- `trace_id`
- `conversation_id`
- `reply.text`
- `actions`
- `handoff.required`
- `handoff.reason`
- `confidence`
- `tool_trace`

Exemplo:
```json
{
  "trace_id": "uuid",
  "conversation_id": "conv-001",
  "reply": {
    "text": "Encontrei 2 opções. Você sabe se é motor 1.6 ou 2.0?"
  },
  "actions": [
    {
      "type": "request_info",
      "key": "engine",
      "prompt": "Qual motorização?",
      "options": ["1.6", "2.0", "Não sei"]
    }
  ],
  "handoff": { "required": false, "reason": null },
  "confidence": 0.82,
  "tool_trace": [
    {
      "tool": "search_parts",
      "status": "ok",
      "elapsed_ms": 42
    }
  ]
}
```

---

## 5. Regras de Negócio Estruturadas (RB)

### RB-01 — Ambiguidade
- Se a consulta tiver múltiplas interpretações (modelo, ano, motorização), o agent deve pedir desambiguação via `actions`.

### RB-02 — Sem resultados
- Se nenhuma peça for encontrada, responder com orientação clara e sugerir próximos dados necessários.
- Se aplicável, usar `handoff.required = true` para sinalizar atendimento humano.

### RB-03 — Dados insuficientes
- Se faltarem dados mínimos para busca (ex.: veículo incompleto), o agent deve pedir informação adicional antes de continuar.

### RB-04 — Handoff
- Quando houver bloqueio técnico ou baixa confiança persistente:
  - definir `handoff.required = true`
  - preencher `handoff.reason` com motivo objetivo

### RB-05 — Confiança
- `confidence` deve refletir a qualidade da resposta (0 a 1).
- Em cenários incertos, reduzir `confidence` e explicitar a incerteza no texto.

---

## 6. Estrutura Mínima de Projeto

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

---

## 7. Requisitos Não-Funcionais (RNF)

### RNF-01 — Containerização
- O agent deve rodar em Docker com build reprodutível.
- Deve existir `Dockerfile` funcional para ambiente de desenvolvimento/integração.

### RNF-02 — Configuração por ambiente
- Variáveis mínimas recomendadas:
  - `APP_ENV`
  - `LOG_LEVEL`
  - `AGENT_PORT` (default `8001`)
  - `DEFAULT_LOCALE` (default `pt-BR`)
  - `DEFAULT_TIMEZONE` (default `America/Sao_Paulo`)

### RNF-03 — Observabilidade
- Logs estruturados em JSON.
- Correlação obrigatória por `trace_id` e `conversation_id`.

### RNF-04 — Resiliência
- Exceções de tools não devem derrubar o serviço.
- O endpoint `/respond` deve retornar erro controlado e rastreável.

---

## 8. Critérios de Aceite (Definition of Done)

### CA-01 — Infraestrutura
- `docker-compose up` sobe o `docker-agent`.
- `GET /health` retorna `200` com status esperado.

### CA-02 — Contrato
- `POST /respond` aceita payload do contrato v1.0.
- Resposta contém `reply`, `actions`, `handoff`, `confidence`, `tool_trace`.

### CA-03 — Regras de decisão
- Casos de ambiguidade geram pergunta de esclarecimento.
- Casos sem resultado retornam orientação e/ou `handoff`.

### CA-04 — Logs
- Todas as requisições registram `trace_id`, latência e resultado.

---

## 9. Entregáveis do v0.1

### Documentação
- `README.md` com instruções de execução.
- `docs/estrutura.md` com requisitos e arquitetura mínima.

### Código
- API FastAPI com rotas `health` e `respond`.
- Modelos Pydantic do contrato.
- Use case de processamento com regras mínimas.
- Tool mock inicial para validação de fluxo.

### Infra
- `Dockerfile`.
- `docker-compose.yml` (standalone e pronto para integração com comm).
- `.env.example` com variáveis necessárias.

---

## 10. Próximas Evoluções (v0.2+)

### EV-01 — Integrações reais
- Substituir tools mock por integrações com ERP/banco/serviços de catálogo.

### EV-02 — Busca semântica
- Adicionar RAG/vetor para recuperação de contexto técnico.

### EV-03 — Observabilidade avançada
- OpenTelemetry + métricas de negócio.

### EV-04 — Segurança
- Autenticação/autorização robusta entre comm e agent.

### EV-05 — Qualidade de resposta
- Estratégias de avaliação contínua e melhoria do agente (prompts, regras, fallback).

13. Próximas Evoluções (v0.2+)

Substituir tool mock por tool real (API do catálogo / SQL / Elastic)

Introduzir LLM real para extração de entidades e decisão de tool calling

Adicionar RAG (documentos estáticos)

Adicionar avaliação offline e dataset para fine-tuning

Definir políticas de guardrails e anti-alucinação