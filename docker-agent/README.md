# docker-agent (v0.1)

Servico FastAPI do agente especialista para receber chamadas do `docker-comm` em `POST /respond`, aplicar regras de negocio minimas e devolver resposta estruturada no contrato v1.0.

## Requisitos

- Docker e Docker Compose
- Ou Python 3.11+ para execucao local

## Estrutura

```text
docker-agent/
  app/
  db/
    init/
      pre_search_init.sql
      csv/
  docs/
    README.md
    TODO.md
    assets/
      datasets/
      db_bootstrap_csv/
      llm/
    training/
      pre_search_fine_tuning.md
    archive/
  scripts/
    README.md
    db/
    eval/
    training/
  trainer/
  tests/
  Dockerfile
  docker-compose.yml
  .env.example
  README.md
```

Leitura rapida da hierarquia:
- `db/`: schema e bootstrap do banco
- `scripts/db`: operacao e carga do banco
- `scripts/eval`: benchmark e avaliacao
- `scripts/training`: revisao, exportacao, empacotamento e ciclo de fine-tuning
- `docs/assets`: datasets e insumos auxiliares
- `docs/training`: guia vivo de treino
- `docs/archive`: material historico, nao normativo

## Configuracao

1. Copie `.env.example` para `.env`
2. Ajuste as variaveis se necessario:
   - `LOG_LEVEL`
   - `AGENT_PORT`
   - `DEFAULT_LOCALE`
   - `DEFAULT_TIMEZONE`
   - `CATALOG_DB_ENABLED`
   - `CATALOG_DB_HOST`
   - `CATALOG_DB_PORT`
   - `CATALOG_DB_NAME`
   - `CATALOG_DB_USER`
   - `CATALOG_DB_PASSWORD`
   - `CATALOG_DB_CONNECT_TIMEOUT_S`
   - `ERP_DB_ENABLED`
   - `ERP_DB_HOST`
   - `ERP_DB_PORT`
   - `ERP_DB_NAME`
   - `ERP_DB_USER`
   - `ERP_DB_PASSWORD`
   - `ERP_DB_CONNECT_TIMEOUT_S`
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

Banco de conhecimento (catalogo pre-search):
- Postgres em `localhost:5433`
- Schema consolidado, seed, dataset de fine-tuning e fila de revisao em `db/init/pre_search_init.sql`
- Modelo de dominio + aliases:
  - `pre_search_brand` + `pre_search_brand_alias`
  - `pre_search_model` + `pre_search_model_alias`
  - `pre_search_part_group`
  - `pre_search_part_type` + `pre_search_part_alias`
  - `pre_search_part_rule`
  - `pre_search_engine_option`
  - `pre_search_invalid_slot_token`
  - `pre_search_part_code_pattern`
  - `pre_search_fine_tuning_dataset`
  - `pre_search_fine_tuning_example`
  - `pre_search_fine_tuning_run`

## Carga de CSV (catalogo real)
Modelo operacional deste projeto: **sem migrations**.  
Fonte unica de bootstrap: `db/init/pre_search_init.sql`.

Se o schema mudar, recrie o volume do Postgres para reaplicar o `init`:

```powershell
docker compose down -v
docker compose up -d --build
```

Se voce ja tem volume ativo e quer reaplicar o schema consolidado sem recriar o banco:

```bash
python scripts/db/apply_sql_file.py \
  --sql-file db/init/pre_search_init.sql \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Para nascer com cobertura completa automaticamente:
- coloque os CSVs reais em `db/init/csv/` com estes nomes:
  - `grupo.csv`
  - `subgrupo.csv`
  - `pre_search_part_rule.csv`
  - `vehicle_brand.csv`
  - `vehicle_model.csv`
  - `engine_option.csv`
- suba a stack com volume novo; o `pre_search_init.sql` ja faz o bootstrap por CSV no startup.

Depois rode a importacao:

```bash
python scripts/db/import_pre_search_catalog_csv.py \
  --grupo-csv "C:\Users\Desktop\Downloads\entregavel\grupo.csv" \
  --subgrupo-csv "C:\Users\Desktop\Downloads\entregavel\subgrupo.csv" \
  --part-rule-csv "C:\Users\Desktop\Downloads\entregavel\pre_search_part_rule.csv" \
  --vehicle-brand-csv "C:\Users\Desktop\Downloads\entregavel\vehicle_brand.csv" \
  --vehicle-model-csv "C:\Users\Desktop\Downloads\entregavel\vehicle_model.csv" \
  --engine-option-csv "C:\Users\Desktop\Downloads\entregavel\engine_option.csv" \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Ou, mantendo os arquivos no projeto (`db/init/csv/`):

```bash
python scripts/db/import_pre_search_catalog_csv.py \
  --grupo-csv "db/init/csv/grupo.csv" \
  --subgrupo-csv "db/init/csv/subgrupo.csv" \
  --part-rule-csv "db/init/csv/pre_search_part_rule.csv" \
  --vehicle-brand-csv "db/init/csv/vehicle_brand.csv" \
  --vehicle-model-csv "db/init/csv/vehicle_model.csv" \
  --engine-option-csv "db/init/csv/engine_option.csv" \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Observacoes:
- `pre_search_part_rule.csv` usa delimitador `;`.
- `subgrupo.csv` repete `cd_subgrupo` em grupos diferentes; portanto `pre_search_part_rule.csv` deve obrigatoriamente ter chave composta: `cd_grupo + part_type_id` (ou `cd_subgrupo`).
- `vehicle_model.csv` atual nao traz marca por linha. O importador usa `--default-model-brand` (padrao: `SEM_MARCA_MAPEADA`).
- Linhas com placeholders (`-`, vazio, codigos entre parenteses) sao ignoradas na carga.
- O script Python de importacao segue util para recarga incremental sem derrubar o volume.
- Templates de CSV ficam em `docs/assets/db_bootstrap_csv/`; eles servem como referencia de formato, nao como fonte operacional carregada automaticamente.

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
- catalogo de pre-search:
  - modo strict: exige Postgres (`presearch-db`) com dados carregados
  - sem fallback hardcoded em memoria
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

### Como `confidence` e `next_question` sao definidos
- `confidence` vem primariamente da resposta da LLM.
- Se houver fallback de parsing de JSON da LLM, `confidence` passa para `0.6`.
- Se a LLM nao informar `next_question` valida e houver `missing_fields`, o sistema gera pergunta padrao por chave faltante.
- Exemplo: faltando `part_query`, a pergunta padrao e `Qual peca voce precisa?`.

## Usar LLM local (Ollama)

1. Escolha como vai rodar o Ollama:
   - no host
   - ou no container `ollama` desta stack
2. Baixe o modelo:
   - no host: `ollama pull qwen2.5:7b`
   - no container: `docker exec ollama ollama pull qwen2.5:7b`
3. Configure no `.env`:
   - `LLM_BASE_URL=http://host.docker.internal:11434`
   - `LLM_MODEL=qwen2.5:7b`
   - `LLM_THINK=false`
4. Suba o container do agente.

Opcional: use o catalogo seed em `docs/assets/llm/pre_search_category_catalog_seed.txt` via `LLM_CATEGORIES_FILE`.

Observacoes:
- se voce usa `LLM_BASE_URL=http://ollama:11434`, o modelo precisa existir dentro do container `ollama`
- se voce rodar `docker compose down -v`, o volume do `ollama` pode ser recriado; nesse caso, faca `docker exec ollama ollama pull qwen2.5:7b` novamente
- se o modelo nao existir no `ollama`, o `/respond` retorna `503` com `Validador de pesquisa indisponivel no momento.`

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
- `docs/assets/datasets/pre_search_eval_dataset_mvp.json`

Rodar avaliacao:

```bash
python scripts/eval/evaluate_pre_search.py
```

Metricas calculadas:
- `decision_accuracy_pct`
- `slot_extraction_accuracy_pct` (part_query, vehicle_brand, vehicle_model, vehicle_year, engine, side)
- `next_question_utility_pct` (match da chave da pergunta esperada)

## Fine-tuning

O projeto agora separa 3 coisas:
- catalogo operacional do pre-search
- dataset rotulado de treino/validacao
- historico de runs de fine-tuning

Fluxo minimo:
1. rotule exemplos no Postgres (`pre_search_fine_tuning_dataset` + `pre_search_fine_tuning_example`)
2. exporte os arquivos de treino:

```bash
python scripts/training/export_pre_search_fine_tuning_dataset.py \
  --dataset-slug pre-search-ft-v1 \
  --output-dir .tmp/fine_tuning \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Arquivos gerados:
- `train.messages.jsonl`
- `validation.messages.jsonl`
- `train.records.jsonl`
- `validation.records.jsonl`
- `system_prompt.txt`
- `manifest.json`

Observacoes:
- `messages.jsonl` serve para providers que treinam em formato de conversa (`system`/`user`/`assistant`).
- `records.jsonl` serve como formato canonico do projeto para auditoria e reuso.
- O exportador monta o mesmo payload usado em runtime: `message_text`, `last_messages`, `dictionary_seed_criteria` e `score_policy`.
- O projeto **nao executa fine-tuning dentro do Ollama**. O treino acontece fora do runtime da API. Depois do treino, voce importa/publica o artefato treinado no Ollama e aponta `LLM_MODEL` para esse novo modelo.

## Fila de revisao

Cada chamada valida ao `/respond` pode ser capturada automaticamente em `pre_search_review_interaction`.

Variavel de controle:
- `PRE_SEARCH_REVIEW_CAPTURE_ENABLED=true`

Listar fila pendente:

```bash
python scripts/training/review_pre_search_queue.py list --status pending --limit 20
```

Marcar decisao correta:

```bash
python scripts/training/review_pre_search_queue.py review \
  --interaction-id 12 \
  --decision ask \
  --question-key engine \
  --question-prompt "Qual a motorizacao do veiculo?" \
  --notes "Deveria perguntar engine, nao handoff"
```

Promover para o dataset de fine-tuning:

```bash
python scripts/training/review_pre_search_queue.py promote \
  --dataset-slug pre-search-ft-v1 \
  --split train \
  --interaction-id 12
```

Campos importantes da fila:
- decisao prevista (`predicted_decision`)
- decisao revisada (`reviewed_decision`)
- pergunta correta (`reviewed_question_key` + `reviewed_question_prompt`) quando `ask`
- referencia de promocao para treino (`promoted_dataset_slug`, `promoted_example_key`)

## Ciclo Automatizado de Modelo

O comando abaixo orquestra:
- exportacao do dataset
- chamada de um treinador externo
- publicacao opcional do modelo candidato
- benchmark do candidato contra o modelo atual usando o golden set
- promocao automatica para `LLM_MODEL` se o candidato ficar melhor

Exemplo:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py \
  --dataset-slug pre-search-ft-v1 \
  --train-command "python tools/train.py --train {train_messages_file} --validation {validation_messages_file} --base-model {base_model} --target-model {target_model}" \
  --publish-command "ollama create {target_model} -f {run_dir}\\Modelfile" \
  --promote-if-better \
  --restart-agent
```

Observacoes:
- `--candidate-model` permite comparar/promover um modelo que ja exista no servidor de inferencia, sem treinar de novo.
- o nome do modelo candidato pode ser fixado com `--target-model-name` ou gerado automaticamente por `FT_TARGET_MODEL_PREFIX`.
- a promocao automatica atualiza `LLM_MODEL` no arquivo definido por `FT_ACTIVE_ENV_FILE` e, se voce usar `--restart-agent`, roda `docker compose up -d docker-agent`.

## Empacotar no Ollama

Se voce ja tiver um artefato treinado externamente, gere um `Modelfile` para importar no Ollama:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path "C:\\caminho\\para\\adapter" \
  --base-model qwen2.5:7b
```

Se voce quiser executar a criacao no Ollama local do host:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path "C:\\caminho\\para\\adapter" \
  --base-model qwen2.5:7b \
  --create
```

Se voce usa o Ollama em Docker, o `docker-compose.yml` agora monta `./.tmp/ollama_models` em `/ollama_models` dentro do container. Nesse caso:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path "C:\\caminho\\para\\adapter" \
  --base-model qwen2.5:7b \
  --create \
  --create-via-docker
```

## Trainer Docker

O projeto agora tem uma imagem separada para treino real:
- serviço `trainer`
- Dockerfile: [trainer/Dockerfile](/d:/TCC/docker-agent/trainer/Dockerfile:1)
- script de treino: [train_pre_search_adapter.py](/d:/TCC/docker-agent/trainer/train_pre_search_adapter.py:1)

Papel do `trainer`:
- ler `train.messages.jsonl` e `validation.messages.jsonl`
- fazer fine-tuning LoRA/QLoRA em um modelo base do Hugging Face
- salvar o adapter em `output-dir/adapter`
- deixar o adapter pronto para importacao no Ollama

Importante:
- o treino usa **model ID do Hugging Face**, nao o nome do modelo no Ollama
- exemplo de base para treino: `Qwen/Qwen2.5-7B-Instruct`
- exemplo de nome final no Ollama: `pre-search-qwen2.5-ft-v1`

### Pre-requisitos

- GPU NVIDIA com Docker Desktop/Engine com suporte a GPU habilitado
- espaco em disco para cache do modelo
- opcionalmente `HF_TOKEN` se o modelo exigir autenticacao

Perfil validado para primeira execucao:
- RTX 5060 16 GB: deve conseguir rodar o fluxo default com QLoRA 4-bit, `batch_size=1`, `gradient_accumulation=8` e `max_seq_length=1024`
- se houver `CUDA out of memory`, o primeiro ajuste recomendado e `TRAINER_MAX_SEQ_LENGTH=768` ou `512`

### Build

```bash
docker compose --profile trainer build trainer
```

Check rapido de GPU dentro da trainer:

```bash
docker compose --profile trainer run --rm trainer python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"
```

### Treino manual

1. Exporte o dataset:

```bash
python scripts/training/export_pre_search_fine_tuning_dataset.py \
  --dataset-slug pre-search-ft-v1 \
  --output-dir .tmp/fine_tuning
```

2. Rode o treino:

```bash
docker compose --profile trainer run --rm trainer \
  python trainer/train_pre_search_adapter.py \
  --train-file .tmp/fine_tuning/pre-search-ft-v1/train.messages.jsonl \
  --validation-file .tmp/fine_tuning/pre-search-ft-v1/validation.messages.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir .tmp/trainer_runs/pre-search-qwen2.5-ft-v1
```

Saida principal:
- adapter em `.tmp/trainer_runs/pre-search-qwen2.5-ft-v1/adapter`
- resumo em `.tmp/trainer_runs/pre-search-qwen2.5-ft-v1/training_summary.json`

3. Importe no Ollama:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path ".tmp\\trainer_runs\\pre-search-qwen2.5-ft-v1\\adapter" \
  --base-model qwen2.5:7b \
  --create \
  --create-via-docker
```

### Ciclo completo automatizado

Fluxo recomendado na maquina com GPU:

1. Suba a stack base:

```bash
docker compose up -d --build
```

2. Garanta que o modelo base do Ollama exista:

```bash
docker exec ollama ollama pull qwen2.5:7b
```

3. Rode o ciclo completo:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py --promote-if-better --restart-agent
```

Comportamento padrao desse comando:
- exporta o dataset
- builda a imagem `trainer`
- roda o treino do adapter
- copia o adapter para a area montada do `ollama`
- importa o adapter no Ollama como novo modelo versionado
- compara modelo atual vs candidato
- promove se o candidato ficar melhor
- reinicia o `docker-agent`

Observacoes:
- na primeira execucao, a `trainer` baixa o modelo base do Hugging Face; isso pode levar varios minutos
- o nome do modelo novo e gerado automaticamente a partir de `FT_TARGET_MODEL_PREFIX`
- se o benchmark nao mostrar melhora, o `.env` nao e alterado
- a promocao altera `LLM_MODEL` em `FT_ACTIVE_ENV_FILE` e depois roda `docker compose up -d docker-agent`

Se voce quiser ver o equivalente explicito, o fluxo default corresponde a algo nesta linha:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py \
  --dataset-slug pre-search-ft-v1 \
  --train-command "docker compose --profile trainer run --rm trainer python trainer/train_pre_search_adapter.py --train-file {train_messages_file_in_container} --validation-file {validation_messages_file_in_container} --base-model Qwen/Qwen2.5-7B-Instruct --output-dir {trainer_output_dir_in_container}" \
  --publish-command "python scripts/training/package_pre_search_ollama_model.py --model-name {target_model} --artifact-kind adapter --artifact-path {adapter_dir} --base-model qwen2.5:7b --create --create-via-docker" \
  --promote-if-better \
  --restart-agent
```

O que esse comando faz:
- exporta o dataset do banco
- chama a docker `trainer`
- gera o adapter
- importa o adapter no Ollama como um novo modelo
- compara modelo atual vs novo no golden set
- se o novo ganhar, troca `LLM_MODEL` no `.env`
- reinicia o `docker-agent`

Exemplo de uso apos treino:
- antes: `LLM_MODEL=qwen2.5:7b`
- depois: `LLM_MODEL=pre-search-qwen2.5-ft-v1`

Guia detalhado:
- `docs/training/pre_search_fine_tuning.md`

## TODO de Implementacao

- Ver roadmap operacional em `docs/TODO.md`.
