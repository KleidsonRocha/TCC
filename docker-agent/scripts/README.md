# Scripts do projeto

O runtime fica em `app/`. Os scripts sao ferramentas de avaliacao, operacao do catalogo, manutencao do ERP, testes e treinamento; nao fazem parte do caminho de cada requisicao.

## Avaliacao (`eval/`)

### Fluxo rotineiro

- `generate_eval_report.py` combina a avaliacao MVP, o benchmark golden e o sweep de `LLM_NUM_PREDICT`; pode incluir resultados de bateria ja executada.
- `run_real_respond_battery.py` executa cenarios contra `POST /respond` e grava os resultados em `.tmp/eval/`.
- `build_real_respond_battery_dataset.py` regenera os 168 cenarios/206 turnos
  estruturais, incluindo os oito `audit_identity_*`/`audit_follow_up_*` de
  19/10/2026. Essa geracao nao altera a comparacao congelada nem aprova rotulos
  comerciais. Regressao sem LLM em `tests/test_request_identity_follow_up.py`.
  O lote de curadoria acrescenta nove `curation_*`; controles SQL e de atributos
  tipados ficam em `tests/test_family_curation_refinements.py`.

```powershell
python -m scripts.eval.generate_eval_report
python -m scripts.eval.run_real_respond_battery --dataset docs/assets/datasets/battery_real_omnichannel_250.json
```

O relatorio consolidado pode ser gerado sem as execucoes demoradas:

```powershell
python -m scripts.eval.generate_eval_report --skip-mvp-eval --skip-golden-benchmark --skip-num-predict-sweep
```

### Avaliadores e diagnosticos pontuais

- `evaluate_pre_search.py`: roda apenas a avaliacao do dataset MVP.
- `benchmark_llm_num_predict.py`: benchmark isolado para `LLM_NUM_PREDICT`.
- `benchmark_pre_search_latency.py`: mede caminhos LLM/deterministicos e diagnostica warmup, idle e `LLM_KEEP_ALIVE`.
- `evaluate_erp_search.py`: avalia **52 casos** e fixtures de identidade/aplicacao e viscosidade de lubrificantes. `--integration-sql <arquivo-local>` adiciona auditoria dos SELECTs de origem.
- `build_real_ranking_annotation_template.py`: cria uma ficha JSON por consulta capturada, sem rotulos de verdade e sem sobrescrever ficha existente.
- `evaluate_real_ranking.py`: calcula Top-1/Top-3 de compatibilidade, preferencia confirmada, incompatibilidades e no-match usando rotulos humanos e um JSON de execucao da bateria real.
- `build_part_family_coverage_dataset.py` e `evaluate_part_family_coverage.py`: geram casos temporarios a partir dos aliases do catalogo e avaliam a cobertura do extractor. O builder e importado pelos testes; nao e uma fonte de golden rotulado.

```powershell
python -m scripts.eval.evaluate_erp_search
python -m scripts.eval.evaluate_part_family_coverage
```

### Cobertura Conversacional Por Categoria/Subcategoria

- `evaluate_category_search.py`: gera uma pergunta por categoria/subcategoria
  ativa do catalogo e responde perguntas incrementais com dados de um item e
  sua aplicacao na fonte ERP (ou snapshot, identificado no relatorio).
- Executa o use case real em processo isolado com o checkout atual; nao testa
  transporte WhatsApp/Redis nem substitui a API em execucao. A captura para a
  fila de treinamento e desabilitada. Consultas de referencia sao somente leitura.
- Salva `cases.json`, `report.json`, `report.md` e `report.html` filtravel em
  `.tmp/eval/category_search/<data>/`, incluindo referencia, todos os turnos,
  produtos apresentados e diagnosticos de busca.
- Julgamentos automaticos sao triagem para revisao humana: coerencia com
  cadastro nao certifica encaixe comercial. Uma referencia por subcategoria
  nao demonstra recuperacao de todos os itens; a selecao examina ate 20 itens
  por subcategoria e pode nao encontrar uma aplicacao com todos os dados.

```bash
python -m scripts.eval.evaluate_category_search --reference-queries
python -m scripts.eval.evaluate_category_search --reference-queries --include-unmapped-source
python -m scripts.eval.evaluate_category_search --case-id sub-17-2 --case-id group-2
```

`--reference-queries` gera pedidos com alias e dados conhecidos de um item real,
sem codigo; o modo sem flag comeca apenas pelo nome da categoria/subcategoria.
Os protocolos sao identificados no relatorio. Retomada usa `--resume-dir`;
`--include-unmapped-source` inclui grupos/subgrupos com produtos no ERP ausentes
do catalogo ativo, sem alterar o catalogo. `consolidate_category_search.py`
combina execucoes completas sem IDs duplicados e recupera confirmacoes textuais
de um unico item somente quando o codigo consta da busca registrada.
Com `--watch`, o consolidator salva uma versao parcial revisada e aguarda
o fim das baterias para substitui-la pelo resultado completo no mesmo local.
Tambem gera `questions.md` com todas as perguntas e referencias planejadas.
`--retry-errors` preserva e repete erros operacionais. A fila residual tem
agendamento proprio no avaliador e nao representa benchmark de carga da API.

### Manutencao da bateria versionada

- `build_real_respond_battery_dataset.py` recompila `battery_structural_respond_v2.json` a partir dos cenarios curados no proprio script e do caderno ERP. Tambem escreve `real_respond_battery_human_validation.md`.

Esse builder e importado pelos testes de reprodutibilidade. Executa-lo altera arquivos versionados; confira o diff antes de aceitar o resultado e preserve anotacoes humanas feitas fora dos dados-fonte.

## Catalogo (`catalog/`)

- `apply_catalog_alias_updates.py`: aplica aliases e aliases de versao ao banco de catalogo; por padrao valida com rollback, `--apply` persiste. Tambem atualiza regras e escopos curados de busca.
- `generate_model_brand_review.py`: cria uma fila local de modelos sem marca confirmada, sem inferir fabricante.
- `import_model_brand_review.py`: valida uma revisao humana e promove os mapeamentos aprovados para `vehicle_model_brand.csv`.

Os dois scripts de marca formam um fluxo unico de curadoria, documentado em [runtime e bootstrap](../docs/guide/runtime_and_bootstrap.md). Arquivos de trabalho ficam em `.tmp/catalog/`.

## ERP (`erp/`)

- `export_search_snapshot.py`: exporta as views v2 instaladas no ERP, sem aplicar DDL.
- `install_search_snapshot.py`: valida com rollback; `--apply` instala o snapshot local e preserva backup.

Os comandos e pre-condicoes estao em [integracao de busca ERP](../docs/guide/erp_search_integration.md).

## Testes (`testing/`)

- `run_quality_checks.ps1`: wrapper Windows para buildar a imagem `docker-agent`, executar `pytest` e, opcionalmente, mutation testing.
- `run_mutation_tests.py`: executa perfis curados de mutation testing.

Uso detalhado em [comandos operacionais](../docs/guide/operational_commands.md).

## Treinamento (`training/`)

- `review_pre_search_queue.py`: revisa interacoes reais e promove exemplos aprovados.
- `export_pre_search_fine_tuning_dataset.py`: exporta os exemplos rotulados do Postgres.
- `rebalance_pre_search_fine_tuning_dataset.py`: ajusta a distribuicao do conjunto exportado.
- `package_pre_search_ollama_model.py`: prepara o `Modelfile` e publica o modelo no Ollama.
- `run_pre_search_fine_tuning_cycle.py`: orquestra exportacao, treino, benchmark e promocao.

O fluxo completo e documentado em [fine-tuning do pre-search](../docs/training/pre_search_fine_tuning.md).

## Retencao

Nao identifiquei scripts claramente descartaveis: os utilitarios de manutencao sao referenciados por documentacao ou testes, e alguns sao importados como modulos. Os avaliadores pontuais podem ficar fora da rotina diaria, mas continuam reproduziveis e geram saidas temporarias. O bootstrap do banco permanece em `db/init/pre_search_init.sql`, nos seeds `db/init/csv/` e no snapshot `db/init/fallback/v2/`; nao existe pasta ativa `scripts/db/`.
