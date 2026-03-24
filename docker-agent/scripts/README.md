# Mapa De Scripts

Este diretorio concentra automacoes auxiliares. O runtime principal continua em `app/`, enquanto `scripts/` cobre avaliacao offline e evolucao do modelo.

## Divisao

- `eval/`
  Scripts de benchmark e avaliacao offline.
- `training/`
  Scripts de revisao, exportacao de dataset, empacotamento de modelo e ciclo de treino.

Observacao:
- o bootstrap do banco ficou centralizado em `db/init/pre_search_init.sql` + `db/init/csv/`
- nao ha mais fluxo versionado de importacao manual por CSV em `scripts/db/`

## Scripts Principais

### `eval/`

- `evaluate_pre_search.py`
  Roda avaliacao funcional no dataset MVP.
- `benchmark_llm_num_predict.py`
  Compara configuracoes de `LLM_NUM_PREDICT`.
- `benchmark_pre_search_latency.py`
  Mede latencia do `pre_search_validator` em sequencia e apos idle.
  Serve para revalidar `LLM_KEEP_ALIVE`, warmup e cold start.

### `training/`

- `export_pre_search_fine_tuning_dataset.py`
  Exporta dataset rotulado do Postgres.
- `review_pre_search_queue.py`
  Revisa interacoes reais e promove para treino.
- `package_pre_search_ollama_model.py`
  Cria `Modelfile` e publica modelo no Ollama.
- `run_pre_search_fine_tuning_cycle.py`
  Orquestra exportacao, treino, benchmark e promocao.

## Leitura

- para medir qualidade: va para `eval/`
- para treino e melhoria de modelo: va para `training/`
