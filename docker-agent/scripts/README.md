# Mapa De Scripts

Este diretorio concentra automacoes auxiliares. O runtime principal continua em `app/`, enquanto `scripts/` cobre avaliacao e evolucao do modelo.

## Divisao

- `eval/`
  Avaliacao offline, bateria real e diagnosticos auxiliares.
- `erp/`
  Exportacao das views do banco quente e validacao/instalacao do snapshot local.
- `testing/`
  Ferramentas de suporte a `pytest` e mutation testing curado com `mutmut`.
- `training/`
  Revisao, exportacao de dataset, empacotamento de modelo e ciclo de treino.

Observacao:
- o bootstrap do banco ficou centralizado em `db/init/pre_search_init.sql`, seeds `db/init/csv/` e snapshot `db/init/fallback/v2/`
- nao ha mais fluxo versionado de importacao manual por CSV em `scripts/db/`

## Fluxo Recomendado

Para avaliacao conversacional, os dois entrypoints principais de `eval/` sao:

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
python .\scripts\eval\run_real_respond_battery.py --dataset docs/assets/datasets/battery_real_omnichannel_250.json
```

Smoke rapido do consolidado:

```powershell
python .\scripts\eval\generate_eval_report.py --skip-mvp-eval --skip-golden-benchmark --skip-num-predict-sweep
```

Relatorios novos sao gravados em `.tmp/eval/`, fora do Git. Para incluir uma
bateria anterior no consolidado, informar `--real-battery-json` com o JSON
gerado pelo runner; o gerador nao reutiliza automaticamente o relatorio de marco.

A execucao completa pode demorar varios minutos, pois avalia a LLM no MVP e
no golden set. O smoke valida a geracao dos arquivos; inclui uma bateria real
somente se seu JSON estiver disponivel no caminho informado.

## Busca ERP

- `python -m scripts.erp.export_search_snapshot`: exporta as views v2 instaladas;
  nao depende de arquivo SQL externo nem aplica DDL no ERP.
- `python -m scripts.erp.install_search_snapshot`: valida carga com rollback;
  `--apply` instala localmente e preserva as tabelas anteriores em backup.
- `python -m scripts.eval.evaluate_erp_search`: 38 casos do contrato e da copia
  CSV, em tabelas temporarias. `--integration-sql <arquivo-local>` adiciona
  auditoria dos SELECTs de origem (114 verificacoes no total).

Comandos Docker em [operacao](../docs/guide/operational_commands.md#busca-erp-v2-e-snapshot-local).

## Scripts Auxiliares De `eval/`

Os arquivos abaixo permanecem como utilitarios pontuais e nao devem ser tratados como fluxo principal:

- `evaluate_pre_search.py`
  Execucao enxuta do dataset MVP.
- `benchmark_llm_num_predict.py`
  Benchmark isolado apenas para tuning de `LLM_NUM_PREDICT`.
- `benchmark_pre_search_latency.py`
  Compara LLM e bypass deterministico, alem de diagnosticar warmup, idle e `LLM_KEEP_ALIVE`.

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
