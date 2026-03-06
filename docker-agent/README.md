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
   - `LLM_BASE_URL` (ex.: `http://host.docker.internal:11434`)
   - `LLM_MODEL` (ex.: `qwen2.5:7b`)
   - `LLM_TIMEOUT_MS`
   - `LLM_TEMPERATURE`
   - `LLM_NUM_PREDICT`
   - `LLM_THINK` (`false` recomendado para modelos reasoning)
   - `LLM_LOG_RAW_RESPONSE` (`true` para logar retorno bruto da LLM no `docker-agent`)
   - `LLM_CATEGORIES_FILE` (opcional)

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
    "used_tools": ["pre_search_validator", "search_parts"],
    "latency_ms": 12.4
  }
}
```

## Regras implementadas

- `schema_version` diferente de `1.0` retorna HTTP 400
- `message.text` vazio/whitespace retorna HTTP 400
- `pre_search_validator` llm:
  - aplica extracao deterministica por dicionario (`dictionary_seed_criteria`) antes da chamada da LLM
  - usa modelo local via Ollama (`/api/chat`, com fallback para `/api/generate` quando necessario)
  - mergeia slots da LLM com os slots deterministicos quando a LLM deixa campos vazios/invalidos
  - quando a saida da LLM vem inconsistente, faz fallback com `decision` da IA + criterios extraidos do texto cru
  - quando Ollama/modelo esta indisponivel (falha de conexao/timeout HTTP), retorna HTTP 503
- `search_parts` mock:
  - contem `bandeja` -> 2 itens (ambiguidade)
  - contem `filtro de oleo` -> 1 item
  - contem `coxim` -> 1 item
  - caso contrario -> 0 itens
- 0 itens -> `handoff.required=true` e `reason=no_match`
- 2+ itens -> `request_info` + `show_items`
- 1 item -> resposta direta com sugestao de proxima validacao
- `tool_trace` inclui `pre_search_validator` e `search_parts` quando a busca e executada
- logs estruturados com `trace_id`, `conversation_id`, status e latencia

## Usar LLM local (Ollama)

1. Instale e inicie o Ollama no host.
2. Baixe o modelo:
   - `ollama pull qwen2.5:7b`
3. Configure no `.env`:
   - `LLM_BASE_URL=http://host.docker.internal:11434`
   - `LLM_MODEL=qwen2.5:7b`
   - `LLM_THINK=false`
4. Suba o container do agente.

Opcional: use o catalogo seed em `docs/pre_search_category_catalog_seed.txt` via `LLM_CATEGORIES_FILE`.

## Execucao local (sem Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir . --port 8001
```

## Testes

```bash
pytest -q
```

## Avaliacao MVP (Decision/Slots/Utility)

Dataset seed:
- `docs/pre_search_eval_dataset_mvp.json`

Rodar avaliacao:

```bash
python scripts/evaluate_pre_search.py
```

Metricas calculadas:
- `decision_accuracy_pct`
- `slot_extraction_accuracy_pct` (part_query, vehicle_model, vehicle_year, engine, side)
- `next_question_utility_pct` (match da chave da pergunta esperada)
