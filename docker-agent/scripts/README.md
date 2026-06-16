# Mapa De Scripts

Este diretorio concentra automacoes auxiliares. O runtime principal continua em `app/`, enquanto `scripts/` cobre avaliacao e evolucao do modelo.

## Divisao

- `eval/`
  Avaliacao offline, bateria real e diagnosticos auxiliares.
- `testing/`
  Ferramentas de suporte a `pytest` e mutation testing curado com `mutmut`.
- `training/`
  Revisao, exportacao de dataset, empacotamento de modelo e ciclo de treino.

Observacao:
- o bootstrap do banco ficou centralizado em `db/init/pre_search_init.sql` + `db/init/csv/`
- nao ha mais fluxo versionado de importacao manual por CSV em `scripts/db/`

## Fluxo Recomendado

Operacionalmente, `eval/` deve ser usado por apenas dois entrypoints:

- `generate_eval_report.py`
  Gera um relatorio consolidado com:
  - avaliacao offline no dataset MVP
  - benchmark no golden set
  - sweep de `LLM_NUM_PREDICT`
  - resumo da bateria real, quando o JSON existir
- `run_real_respond_battery.py`
  Executa a bateria real contra `POST /respond` e grava:
  - JSON bruto dos casos
  - relatorio Markdown consolidado

Exemplos:

```powershell
python .\scripts\eval\generate_eval_report.py
python .\scripts\eval\run_real_respond_battery.py
```

Smoke rapido do consolidado:

```powershell
python .\scripts\eval\generate_eval_report.py --skip-mvp-eval --skip-golden-benchmark --skip-num-predict-sweep
```

Observacao:
- a execucao completa do consolidado pode demorar varios minutos, porque roda validacoes reais da LLM no dataset MVP e no golden set
- o smoke acima serve apenas para validar o entrypoint, a leitura do JSON real e a geracao dos arquivos finais

## Scripts Auxiliares De `eval/`

Os arquivos abaixo permanecem como utilitarios pontuais e nao devem ser tratados como fluxo principal:

- `evaluate_pre_search.py`
  Execucao enxuta do dataset MVP.
- `benchmark_llm_num_predict.py`
  Benchmark isolado apenas para tuning de `LLM_NUM_PREDICT`.
- `benchmark_pre_search_latency.py`
  Diagnostico de latencia, warmup, idle e `LLM_KEEP_ALIVE`.

## `training/`

- `export_pre_search_fine_tuning_dataset.py`
  Exporta dataset rotulado do Postgres.
- `review_pre_search_queue.py`
  Revisa interacoes reais e promove para treino.
- `package_pre_search_ollama_model.py`
  Cria `Modelfile` e publica modelo no Ollama.
- `run_pre_search_fine_tuning_cycle.py`
  Orquestra exportacao, treino, benchmark e promocao.

## `testing/`

- `run_mutation_tests.py`
  Executa perfis curados de mutation testing nos modulos mais sensiveis sem tentar mutar o projeto inteiro de uma vez.
- `run_quality_checks.ps1`
  Wrapper Windows para buildar a imagem `docker-agent`, rodar `pytest` no container e, opcionalmente, executar mutation testing curado.

## Leitura

- para avaliacao operacional: use os dois entrypoints acima em `eval/`
- para investigacao tecnica pontual: use os scripts auxiliares de `eval/`
- para treino e melhoria de modelo: va para `training/`
