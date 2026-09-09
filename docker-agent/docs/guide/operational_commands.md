# Comandos Operacionais

Execute os comandos abaixo a partir da raiz do projeto: `docker-agent/`.

Este guia concentra o caminho operacional mais curto para a stack atual:
- `docker-agent` expoe a API
- `presearch-db` guarda catalogo, fila de revisao e dataset de fine-tuning
- `ollama` hospeda os modelos de inferencia
- `trainer` e usado apenas quando voce dispara fine-tuning

## Revisar Conversas No Streamlit

Com a stack ativa, acesse `http://localhost:8501` e abra a aba `Revisao de IA`.
A fila `Pendentes` mostra apenas conversas que ainda possuem turnos sem avaliacao;
a fila `Concluidas` permite consultar o que ja foi revisado ou descartado.

Para proteger a operacao, defina o mesmo segredo nos dois projetos:

```env
# docker-agent/.env
REVIEW_API_KEY=troque-por-um-segredo-forte

# docker-comm/.env
REVIEW_API_KEY=troque-por-um-segredo-forte
REVIEWED_BY=nome-do-avaliador
```

Depois recrie `docker-agent` e `docker-comm-ui`. A UI acessa o agent pela rede
interna usando `REVIEW_API_URL`; nao exponha o Postgres para executar a revisao.

## Subir E Derrubar A Stack

Subir ou rebuildar a stack base:

```bash
docker compose up -d --build
```

Derrubar os containers e manter volumes:

```bash
docker compose down
```

Derrubar os containers e recriar os volumes do banco e do Ollama:

```bash
docker compose down -v
docker compose up -d --build
```

Ver status dos containers:

```bash
docker compose ps
```

Seguir logs principais:

```bash
docker compose logs -f docker-agent
docker compose logs -f presearch-db
docker compose logs -f ollama
```

## Validar A API

Health check:

```bash
curl http://localhost:8001/health
```

Exemplo de `POST /respond`:

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

Se a API retornar `Validador de pesquisa indisponivel no momento.`, verifique se o modelo existe no `ollama`:

```bash
docker exec ollama ollama list
docker exec ollama ollama pull qwen2.5:7b
```

## Validar O Banco

Abrir `psql` no container:

```bash
docker exec -it presearch-db psql -U presearch -d presearch
```

Dentro do `psql`, validar as tabelas principais:

```sql
\d pre_search_review_interaction
\d pre_search_fine_tuning_dataset_header
\d pre_search_fine_tuning_dataset_record
\d pre_search_fine_tuning_run
```

Ver as ultimas interacoes capturadas:

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

## Recriar O Catalogo Deterministico

A fonte de bootstrap usada pelo Postgres em um volume novo e:
- `db/init/pre_search_init.sql`
- `db/init/csv/`

Recriar o banco a partir do bootstrap consolidado:

```bash
docker compose down -v
docker compose up -d --build
```

## Rodar Testes

No Windows, o caminho mais direto e usar o wrapper de qualidade. Ele builda a imagem `docker-agent` e roda a suite dentro do container:

```powershell
.\scripts\testing\run_quality_checks.ps1
```

Rodar apenas um subconjunto de testes:

```powershell
.\scripts\testing\run_quality_checks.ps1 -PytestArgs "-q tests/test_rules.py"
```

Rodar a suite completa no container:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q
```

Rodar apenas os testes de regra de negocio:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q tests/test_rules.py
```

Rodar apenas os testes de captura de revisao:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent pytest -q tests/test_process_agent_request_review_capture.py
```

## Mutation Testing

`mutmut` exige ambiente com `fork`. No contexto deste projeto, a forma mais segura de usar isso em Windows e via container Linux do `docker-agent`.

Rodar testes normais e, em seguida, o pacote curado de mutacao:

```powershell
.\scripts\testing\run_quality_checks.ps1 -Mutation -CleanMutation -MutationResults
```

Rodar somente um perfil de mutacao, sem repetir `pytest`:

```powershell
.\scripts\testing\run_quality_checks.ps1 -SkipPytest -Mutation -MutationProfile review_queue -CleanMutation -MutationResults
```

Listar os perfis curados:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent python scripts/testing/run_mutation_tests.py --list
```

Rodar mutacao apenas na fila de revisao:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent python scripts/testing/run_mutation_tests.py review_queue --clean --results
```

Rodar o pacote curado inteiro:

```bash
docker compose run --rm -v d:\TCC\docker-agent:/app docker-agent python scripts/testing/run_mutation_tests.py all_curated --clean --results
```

Perfis atuais:
- `review_queue`
- `export_dataset`
- `training_cycle`
- `format_payloads`

## Fila De Revisao

Listar interacoes pendentes:

```bash
python scripts/training/review_pre_search_queue.py list --status pending --limit 20
```

Revisar uma interacao:

```bash
python scripts/training/review_pre_search_queue.py review \
  --interaction-id 12 \
  --decision ask \
  --question-key engine \
  --question-prompt "Qual a motorizacao do veiculo?" \
  --notes "Deveria pedir engine antes de buscar"
```

Promover uma interacao revisada para o dataset de fine-tuning:

```bash
python scripts/training/review_pre_search_queue.py promote \
  --dataset-slug pre-search-ft-v1 \
  --split train \
  --interaction-id 12
```

## Avaliacao Offline E Benchmark

Rodar o dataset MVP de avaliacao:

```bash
python scripts/eval/evaluate_pre_search.py
```

Rodar o benchmark de `LLM_NUM_PREDICT`:

```bash
python scripts/eval/benchmark_llm_num_predict.py
```

Rodar a bateria de latencia:

```bash
python scripts/eval/benchmark_pre_search_latency.py
```

Validar a selecao da bateria real sem chamar as APIs:

```bash
python scripts/eval/run_real_respond_battery.py --tier extended --dry-run
```

Executar o conjunto critico diretamente no `docker-agent`:

```bash
python scripts/eval/run_real_respond_battery.py --tier smoke
```

Executar um cenario multi-turno pelo `docker-comm` e pelo Redis real:

```bash
python scripts/eval/run_real_respond_battery.py --target comm --tier regression --scenario-id disambiguation_001
```

Se `API_KEY` estiver ativo no `docker-comm`, acrescente `--api-key <valor>`. Filtros por `--category` e `--scenario-id` aceitam repeticao ou valores separados por virgula. Cada rodada integrada usa um `conversation_id` unico para nao herdar estado Redis anterior. As saidas usam nomes unicos em `.tmp/eval/`; um relatorio versionado so e substituido quando `--output-json` ou `--output-md` for informado conscientemente.

## Ciclo De Fine-Tuning

Buildar a imagem de treino:

```bash
docker compose --profile trainer build trainer
```

Validar a disponibilidade de GPU dentro do container de treino:

```bash
docker compose --profile trainer run --rm trainer python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"
```

Rodar o ciclo completo de fine-tuning:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py --promote-if-better --restart-agent
```

O que esse comando faz:
- exporta o dataset a partir do Postgres
- executa o `trainer`
- gera um adapter
- cria um novo modelo no `ollama`
- compara o candidato com o modelo atual no golden set
- atualiza `LLM_MODEL` no `.env` apenas se o candidato for melhor
- reinicia o `docker-agent`

## Fluxo Manual De Fine-Tuning

Exportar o dataset de fine-tuning:

```bash
python scripts/training/export_pre_search_fine_tuning_dataset.py \
  --dataset-slug pre-search-ft-v1 \
  --output-dir .tmp/fine_tuning
```

Treinar o adapter manualmente:

```bash
docker compose --profile trainer run --rm trainer \
  python trainer/train_pre_search_adapter.py \
  --train-file .tmp/fine_tuning/pre-search-ft-v1/train.messages.jsonl \
  --validation-file .tmp/fine_tuning/pre-search-ft-v1/validation.messages.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir .tmp/trainer_runs/pre-search-qwen2.5-ft-v1
```

Empacotar e publicar o adapter no `ollama`:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path ".tmp\\trainer_runs\\pre-search-qwen2.5-ft-v1\\adapter" \
  --base-model qwen2.5:7b \
  --create \
  --create-via-docker
```

## Comandos Comuns De Recuperacao

Recriar a stack inteira e os volumes:

```bash
docker compose down -v
docker compose up -d --build
docker exec ollama ollama pull qwen2.5:7b
```
