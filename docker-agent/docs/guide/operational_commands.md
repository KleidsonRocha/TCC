# Operational Commands

Execute the commands below from the project root: `docker-agent/`.

This guide is the shortest operational path for the current stack:
- `docker-agent` serves the API
- `presearch-db` holds the catalog, review queue and fine-tuning dataset
- `ollama` hosts the inference models
- `trainer` is used only when you trigger fine-tuning

## Start And Stop The Stack

Start or rebuild the base stack:

```bash
docker compose up -d --build
```

Stop the containers and keep volumes:

```bash
docker compose down
```

Stop the containers and recreate the database and Ollama volumes:

```bash
docker compose down -v
docker compose up -d --build
```

Check container status:

```bash
docker compose ps
```

Follow the main service logs:

```bash
docker compose logs -f docker-agent
docker compose logs -f presearch-db
docker compose logs -f ollama
```

## Validate The API

Health check:

```bash
curl http://localhost:8001/health
```

Example `POST /respond`:

```powershell
curl -X POST http://localhost:8001/respond `
  -H "Content-Type: application/json" `
  -d '{
    "schema_version": "1.0",
    "trace_id": "manual-001",
    "conversation_id": "conv-001",
    "message": { "text": "Preciso de bandeja da EcoSport 2008" },
    "business": { "branch_id": 1 }
  }'
```

If the API returns `Validador de pesquisa indisponivel no momento.`, check whether the model exists in `ollama`:

```bash
docker exec ollama ollama list
docker exec ollama ollama pull qwen2.5:7b
```

## Validate The Database

Open `psql` in the container:

```bash
docker exec -it presearch-db psql -U presearch -d presearch
```

Inside `psql`, validate the main tables:

```sql
\d pre_search_review_interaction
\d pre_search_fine_tuning_dataset
\d pre_search_fine_tuning_example
\d pre_search_fine_tuning_run
```

Check the latest captured review interactions:

```sql
SELECT
  id,
  predicted_decision,
  llm_endpoint_used,
  llm_output_valid,
  llm_fallback_used,
  llm_decision_raw,
  created_at
FROM pre_search_review_interaction
ORDER BY id DESC
LIMIT 10;
```

Reapply the consolidated SQL without dropping the database:

```bash
python scripts/db/apply_sql_file.py \
  --sql-file db/init/pre_search_init.sql \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

## Load Or Reload The Deterministic Catalog

The bootstrap source used by Postgres on a fresh volume is:
- `db/init/pre_search_init.sql`
- `db/init/csv/`

Reload the CSV catalog manually:

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

## Run Tests

Run the full test suite in the container:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q
```

Run only business-rule tests:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q tests/test_rules.py
```

Run only review-capture flow tests:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q tests/test_process_agent_request_review_capture.py
```

## Review Queue

List pending interactions:

```bash
python scripts/training/review_pre_search_queue.py list --status pending --limit 20
```

Review one interaction:

```bash
python scripts/training/review_pre_search_queue.py review \
  --interaction-id 12 \
  --decision ask \
  --question-key engine \
  --question-prompt "Qual a motorizacao do veiculo?" \
  --notes "Deveria pedir engine antes de buscar"
```

Promote a reviewed interaction to the fine-tuning dataset:

```bash
python scripts/training/review_pre_search_queue.py promote \
  --dataset-slug pre-search-ft-v1 \
  --split train \
  --interaction-id 12
```

## Offline Evaluation And Benchmark

Run the MVP evaluation dataset:

```bash
python scripts/eval/evaluate_pre_search.py
```

Run the `LLM_NUM_PREDICT` benchmark:

```bash
python scripts/eval/benchmark_llm_num_predict.py
```

## Fine-Tuning Cycle

Build the training image:

```bash
docker compose --profile trainer build trainer
```

Validate GPU availability inside the training container:

```bash
docker compose --profile trainer run --rm trainer python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"
```

Run the full fine-tuning cycle:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py --promote-if-better --restart-agent
```

What this command does:
- exports the dataset from Postgres
- runs the `trainer`
- generates an adapter
- creates a new model in `ollama`
- compares candidate vs current model on the golden set
- updates `LLM_MODEL` in `.env` only if the candidate is better
- restarts `docker-agent`

## Manual Fine-Tuning Flow

Export the fine-tuning dataset:

```bash
python scripts/training/export_pre_search_fine_tuning_dataset.py \
  --dataset-slug pre-search-ft-v1 \
  --output-dir .tmp/fine_tuning
```

Train the adapter manually:

```bash
docker compose --profile trainer run --rm trainer \
  python trainer/train_pre_search_adapter.py \
  --train-file .tmp/fine_tuning/pre-search-ft-v1/train.messages.jsonl \
  --validation-file .tmp/fine_tuning/pre-search-ft-v1/validation.messages.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir .tmp/trainer_runs/pre-search-qwen2.5-ft-v1
```

Package and publish the adapter in `ollama`:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path ".tmp\\trainer_runs\\pre-search-qwen2.5-ft-v1\\adapter" \
  --base-model qwen2.5:7b \
  --create \
  --create-via-docker
```

## Common Recovery Commands

Recreate the whole stack and volumes:

```bash
docker compose down -v
docker compose up -d --build
docker exec ollama ollama pull qwen2.5:7b
```

Restart only the API after changing `.env`:

```bash
docker compose up -d docker-agent
```

List the models currently available in `ollama`:

```bash
docker exec ollama ollama list
```
