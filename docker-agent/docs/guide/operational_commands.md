# Comandos Operacionais

Execute os comandos abaixo a partir da raiz do projeto: `docker-agent/`.

Este guia concentra o caminho operacional mais curto para a stack atual:
- `docker-agent` expoe a API
- `presearch-db` guarda catalogo, fila de revisao e dataset de fine-tuning
- `ollama` hospeda os modelos de inferencia
- `trainer` e usado apenas quando voce dispara fine-tuning

## Busca ERP V2 E Snapshot Local

O runtime corrigido exige `item_search_candidates` e `item_search_applications`
no contrato v2. O SQL operacional do ERP fica fora do Git; a operacao do banco
quente mantem suas definicoes. O exportador consulta as views ja instaladas.

Os comandos abaixo usam o codigo do checkout, mesmo antes do rebuild da imagem.
No PowerShell, execute da raiz do `docker-agent`:

```powershell
# Exporta em UTF-8, em uma transacao somente de leitura no ERP.
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m scripts.erp.export_search_snapshot

# Valida o snapshot inteiro em um schema separado e desfaz a carga.
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m scripts.erp.install_search_snapshot

# Instala localmente e informa o schema de backup das tabelas anteriores.
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m scripts.erp.install_search_snapshot --apply

# Golden set: contrato e COPY de ida/volta do snapshot, em tabelas temporarias.
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m scripts.eval.evaluate_erp_search

# Opcional: audita tambem os SELECTs do SQL externo fornecido localmente.
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m scripts.eval.evaluate_erp_search --integration-sql .tmp/sql/erp_search_integration_candidates_runtime.sql

# Suite completa, incluindo as regressoes PostgreSQL (nao ignorar essas no CI).
docker compose run --rm --no-deps -e ERP_SEARCH_TEST_POSTGRES=1 -v "${PWD}:/app" docker-agent python -m pytest -q
```

O exportador grava o par em `db/init/fallback/v2/` e publica os checksums por
ultimo. O bootstrap rejeita exportacao incompleta/corrompida. O instalador
usa exclusivamente a conexao `CATALOG_DB_*`; o modulo DDL externo nunca e
executado por ele. Guarde o nome do schema de backup para rollback coordenado
com a imagem anterior. Se o ERP ainda usar v1, mantenha o fallback v2 habilitado
durante a migracao; o runtime novo nao deve reutilizar agregados antigos.

No Git, manter `db/init/fallback/v2/*.csv.gz` no LFS e os dois manifestos no
Git comum. A regra `eol=lf` protege os checksums em clones Windows/Linux.
Em clone novo, executar `git lfs pull` antes de inicializar o Postgres. O antigo
CSV v1 e o SQL separado `zz_erp` foram removidos; a carga local esta consolidada.
Relatorios de execucao ficam em `.tmp/eval/`, e o historico resumido em
[HISTORICO.md](../HISTORICO.md).

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
curl --fail http://localhost:8001/ready
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

Os testes ficam em `tests/` e sao agrupados por area. `test_rules.py` cobre
extracao e validacao deterministica; `test_respond.py` cobre o contrato HTTP e
as conversas; os demais modulos cobrem integracoes e fluxos especificos. Cada
funcao de teste precisa ter nome unico dentro do arquivo: uma definicao Python
posterior com o mesmo nome substitui a anterior e impede sua coleta pelo pytest.

Para verificar sintaxe sem executar os testes:

```bash
python -m compileall -q tests
```

Para inspecionar os casos coletados antes de executa-los:

```bash
pytest --collect-only -q tests
```

Para atualizar aliases em um banco existente sem apagar volumes, depois do
backup manual e do build da imagem:

```bash
docker compose run --rm --no-deps docker-agent python -m scripts.catalog.apply_catalog_alias_updates
docker compose run --rm --no-deps docker-agent python -m scripts.catalog.apply_catalog_alias_updates --apply
docker compose up -d --build --no-deps --force-recreate docker-agent
```

Validacao SQL focada do ranking (tabelas temporarias, sem alterar o ERP):

```bash
docker compose exec docker-agent python -m scripts.eval.evaluate_erp_search --output .tmp/eval/erp_search_reranking_report.json
```

Se `.tmp` nao estiver montada, copie o relatorio do container com
`docker cp docker-agent:/app/.tmp/eval/erp_search_reranking_report.json .tmp/eval/`.

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

### Regra Para Casos Reais Encontrados Em Testes

Todo erro funcional relatado durante teste manual deve ganhar uma protecao
versionada antes de ser considerado resolvido. Classifique o caso conforme sua
natureza:

- regra, extracao, decisao, pergunta ou contexto multi-turno estavel: adicionar
  ao `pre_search_num_predict_golden_set.json` e ao teste unitario/API que cobre
  a causa;
- ranking, disponibilidade ou cobertura do ERP: adicionar a regressao de busca
  e a bateria real, sem tornar o golden set dependente de estoque ou de um
  resultado comercial que muda;
- integracao de Redis, gateway ou interface: adicionar um cenario integrado da
  bateria real usando `docker-comm`.

O registro precisa conter a mensagem original, o contexto minimo necessario,
o comportamento esperado e um identificador rastreavel. O objetivo e impedir
que uma correcao futura reintroduza um erro ja observado por um avaliador.

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

Por padrao, a bateria consulta a captura protegida em
`pre_search_review_interaction` depois de cada turno e inclui
`search_diagnostics` nos tres artefatos gerados. O JSON preserva os candidatos
brutos, rejeitados, filtrados e ranqueados e o `score_breakdown`; o Markdown
resume contagens e o primeiro ranqueado. A correlacao usa o `trace_id`: no
alvo `agent`, o id enviado pela bateria; no alvo `comm`, o id gerado pelo
gateway e devolvido na resposta. Isso e somente evidencia interna e nunca faz
parte da resposta do chat.

Se a bateria for executada fora da rede do catalogo, ela continua a rodar e
marca a captura como `unavailable`. A gravacao ocorre antes da resposta HTTP,
portanto a leitura padrao nao espera; use `--no-search-diagnostics` para uma
rodada sem leitura da fila, ou habilite uma tentativa adicional em uma
infraestrutura com replicacao:

```bash
python scripts/eval/run_real_respond_battery.py --tier regression --search-diagnostics-wait-s 2
```

Se `API_KEY` estiver ativo no `docker-comm`, acrescente `--api-key <valor>`. Filtros por `--category` e `--scenario-id` aceitam repeticao ou valores separados por virgula. Cada rodada integrada usa um `conversation_id` unico para nao herdar estado Redis anterior. As saidas usam nomes unicos em `.tmp/eval/`; um relatorio versionado so e substituido quando `--output-json` ou `--output-md` for informado conscientemente.

## Avaliar Todas As Categorias Com Conversas Incrementais

No diretorio `docker-agent`, executar em ambiente com dependencias, catalogo,
fonte ERP/snapshot e Ollama configurados:

```bash
python -m scripts.eval.evaluate_category_search --reference-queries
python -m scripts.eval.evaluate_category_search --reference-queries --include-unmapped-source
```

No PowerShell, para testar os arquivos locais sem rebuild/deploy da API:

```powershell
docker compose run --rm --no-deps -T -v "${PWD}:/app" docker-agent python -m scripts.eval.evaluate_category_search --reference-queries
```

O comando usa as categorias/subcategorias ativas do catalogo e o use case real
em processo isolado. Preserva estado/historico entre turnos e responde somente
com dados da referencia; quando o atributo nao existe, responde `nao sei`.
Nao grava a bateria na fila de revisao/treinamento nem altera ERP ou modelo.
O agendamento permite quatro conversas em andamento por padrao, mas compartilha
limites globais de ate duas inferencias e quatro buscas (respeitando limites
menores configurados). Assim, espera pela LLM nao bloqueia casos deterministicos.
`--concurrency 1` serializa; `--concurrency 32` amplia apenas a fila de casos.
`--max-turns` limita cada conversa (padrao oito).

`--reference-queries` usa um alias nao ambiguo da familia e os dados conhecidos
de um item real no pedido inicial, sem informar seu codigo. Lubrificantes
usam apenas familia e viscosidade. Sem essa flag, a pergunta inicial usa apenas
o nome da categoria/subcategoria, permitindo avaliar complementacao desde o
inicio. Os dois modos sao protocolos diferentes, identificados no relatorio.
O agendamento isola a fila residual no avaliador; os tempos desta bateria nao
constituem um benchmark de carga da API de producao.

Para executar um caso, usar `--case-id sub-17-2` ou `--case-id group-2`.
`--limit` restringe a quantidade; `--samples` controla quantos itens da fonte
sao examinados por subcategoria. Cada execucao cria pasta nova; um
`--output-dir` explicito deve apontar para diretorio ainda inexistente.
Para retomar uma bateria interrompida sem repetir casos concluidos, use
`--resume-dir .tmp/eval/category_search/<data>`. O avaliador conserva as
referencias de `cases.json` e registra a retomada no relatorio; mantenha
modelo, dados e codigo de runtime iguais entre os trechos da execucao.
`--retry-errors` repete somente erros operacionais ao retomar e conserva os
registros anteriores em `previous_error_attempts`.

`--include-unmapped-source` tambem prepara casos de grupos/subgrupos com itens
na fonte, mas ausentes do catalogo ativo, sem modificar o catalogo.
Para reunir baterias completas com IDs distintos, usar:

```bash
python -m scripts.eval.consolidate_category_search --run-dir .tmp/eval/bateria_principal --run-dir .tmp/eval/bateria_complementar --output-dir .tmp/eval/auditoria_consolidada
```

A consolidacao preserva os turnos e recupera confirmacoes textuais de item unico
apenas se o codigo tambem foi retornado pela busca registrada. Os itens
recuperados passam pela mesma verificacao independente da fonte. A ferramenta
recusa execucoes incompletas e IDs repetidos.

Para uma bateria longa, acrescente `--watch` ao consolidator: ele salva um
relatorio parcial revisado e permanece aguardando as entradas terminarem.
Quando todas terminam, substitui os arquivos gerados pelo relatorio completo
no mesmo diretorio. A versao parcial nao recebe `finished_at` e informa o
numero concluido frente ao planejado. O processo precisa continuar ativo;
se a maquina/Docker for desligada, retome primeiro o avaliador.

Os relatorios HTML/JSON/Markdown em `.tmp/eval/category_search/` registram
fonte, modelo, hashes do codigo, quantidade de itens cadastrados, item de
referencia, perguntas/respostas, criterios e produtos apresentados. Use o
HTML para filtrar categoria, codigo ou resultado e abrir as conversas.

Separar suspeitas de falso negativo, itens fora da subcategoria/aplicacao,
categorias sem itens na fonte, falhas operacionais, conversa nao concluida e
handoff por atributo desconhecido. Esses rotulos exigem revisao humana e nao
devem virar golden nem treino automaticamente. O teste cobre uma conversa
por entrada, nao todos os produtos ou todas as aplicacoes, e nao valida o
transporte pelo gateway/WhatsApp.

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

## Regressao De Identidade E Follow-Up

Para curadoria/refinamentos, incluir tambem
`tests/test_family_curation_refinements.py` e executar a suite do gateway com
`RUN_REDIS_INTEGRATION=1`. O estado possui campos novos opcionais, portanto
atualizar agente e gateway no mesmo lote.

No checkout corrigido, executar sem alterar o agente ativo:

```powershell
docker compose run --rm --no-deps -v "${PWD}:/app" docker-agent python -m pytest -q tests/test_request_identity_follow_up.py tests/test_erp_search_tools_pg.py tests/test_real_respond_battery.py
python -m scripts.eval.build_real_respond_battery_dataset
python -m scripts.eval.run_real_respond_battery --dataset docs/assets/datasets/battery_structural_respond_v2.json --tier extended --dry-run
```

Os testes usam dados controlados. Para os controles SQL com tabelas temporarias
e rollback, usar somente PostgreSQL local de testes, nunca credenciais do ERP:

```powershell
docker compose run --rm --no-deps -e ERP_SEARCH_TEST_POSTGRES=1 -v "${PWD}:/app" docker-agent python -m pytest -q
```

A verificacao de 19/10/2026 no snapshot e a conclusao local estao em
[PROGRESS.md](../PROGRESS.md#identidade-e-follow-up-concluidos-localmente-em-19102026).
O snapshot congelado esta em modo somente leitura e nao serve para criar as
tabelas temporarias do golden. O lote posterior de curadoria foi implantado no
Docker local; VPS e canal externo ainda exigem implantacao/reteste conforme
[PROGRESS.md](../PROGRESS.md#curadoria-e-refinamentos-no-docker-local-em-19102026).
Nao recriar volumes para aplicar mudancas de Python.

## Comandos Comuns De Recuperacao

### Atualizacao Controlada De Curadoria Em Volume Existente

Salvar antes um dump custom das tabelas `pre_search_part_alias`,
`pre_search_part_rule`, `pre_search_part_family_scope` e
`pre_search_variant_alias`, e guardar as imagens anteriores com tags de rollback.
O dump desta entrega fica em `.tmp/eval/family_refinements_20261019/catalog_before.dump`.
O manifesto dessa pasta registra hashes e imagens. Fila, datasets e snapshot
nao participam da atualizacao; nao executar `down -v` nem o bootstrap completo.

```powershell
docker compose build docker-agent
docker compose run --rm --no-deps docker-agent python -m scripts.catalog.apply_catalog_alias_updates
docker compose run --rm --no-deps docker-agent python -m scripts.catalog.apply_catalog_alias_updates --apply
docker compose up -d --no-deps --force-recreate docker-agent
```

Na pasta `docker-comm`, construir/recriar somente o gateway:

```powershell
docker compose build docker-comm
docker compose up -d --no-deps --force-recreate docker-comm
```

Conferir `/health`, `/ready` do agente e `/health` do gateway; executar conversas
com origem/IDs exclusivos por `/test/send`, aguardando `completed` com o mesmo
`trace_id`. Verificar estado/historico Redis, versao completa, ABS falso e item
ativo. Esse teste local do gateway nao representa entrega no Omni/Convert externo.

Rollback: selecionar o dump e as tags correspondentes ao mesmo lote; restaurar
somente as quatro tabelas de catalogo, em transacao, e desativar os registros
das duas tabelas de curadoria criadas neste lote. Recriar agente/gateway usando
as imagens anteriores, sem rebuild, e repetir health/ready e controles. Nao
restaurar fila/datasets/snapshot ou apagar Redis para desfazer esta mudanca.
O backup do agente foi recuperado por export/import porque a imagem anterior
tinha metadados incompletos no Docker; o rootfs e a tag de rollback foram
preservados localmente e o import foi verificado, sem carregar credenciais.

Recriar a stack inteira e os volumes:

```bash
docker compose down -v
docker compose up -d --build
docker exec ollama ollama pull qwen2.5:7b
```
