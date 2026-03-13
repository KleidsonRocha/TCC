# Scripts Map

## Hierarquia

- `db/`
  Scripts de schema, carga e manutencao do catalogo no Postgres.
- `eval/`
  Scripts de benchmark e avaliacao offline.
- `training/`
  Scripts de captura revisada, exportacao do dataset, empacotamento no Ollama e ciclo de fine-tuning.

## O que cada grupo faz

### `db/`
- `apply_sql_file.py`: aplica SQL adicional em banco ja existente
- `import_pre_search_catalog_csv.py`: importa catalogo deterministico a partir de CSV

### `eval/`
- `evaluate_pre_search.py`: roda avaliacao no dataset MVP
- `benchmark_llm_num_predict.py`: compara configuracoes de `LLM_NUM_PREDICT`

### `training/`
- `export_pre_search_fine_tuning_dataset.py`: exporta dataset rotulado do Postgres
- `review_pre_search_queue.py`: revisa interacoes reais e promove para treino
- `package_pre_search_ollama_model.py`: cria `Modelfile` e publica modelo no Ollama
- `run_pre_search_fine_tuning_cycle.py`: orquestra exportacao, treino, benchmark e promocao

## Regra de organizacao

- se mexe no Postgres/catalogo: `db/`
- se mede qualidade/desempenho: `eval/`
- se mexe em dataset, modelo ou ciclo de treino: `training/`
