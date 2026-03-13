# Fine-tuning do pre-search

## Objetivo

O fine-tuning aqui serve para adaptar a LLM ao dominio de autopecas, com foco em:
- decidir melhor entre `search`, `ask` e `handoff`
- nao inventar `part_code`
- manter o JSON do validador consistente
- aprender comportamentos de contexto multi-turno

## O que o banco guarda

O Postgres nao guarda "o modelo treinado". Ele guarda o **dataset rotulado** que sera usado no treino.

Tabelas:
- `pre_search_fine_tuning_dataset`: cabecalho do dataset
- `pre_search_fine_tuning_example`: exemplos rotulados de treino/validacao/teste
- `pre_search_fine_tuning_run`: historico de exports e runs de treinamento
- `pre_search_review_interaction`: captura de conversas reais para revisao

Cada exemplo rotulado guarda:
- `input_message_text`
- `input_last_messages`
- `expected_decision`
- `expected_criteria`
- `expected_missing_fields`
- `expected_next_question`
- `expected_confidence`
- `part_code_source`
- `tags`

## Como funciona a etapa de treino

Fluxo real:

1. Voce rotula os exemplos no banco.
2. O script exporta esses exemplos em `JSONL`.
3. Esse `JSONL` vai para uma stack de treino/fine-tuning.
4. A stack de treino gera um **novo modelo ajustado** ou um identificador de modelo treinado.
5. Esse novo modelo e importado/publicado em um servidor de inferencia.
6. A API continua chamando `chat` normalmente, mas agora usando o modelo ajustado.

Ou seja: o banco nao gera um "chat treinado" sozinho.

O resultado do treino e uma destas formas:
- pesos ajustados de um modelo
- adaptador/LoRA
- `model id` publicado em um provedor

Depois disso, a API usa esse resultado da mesma forma que ja usa hoje qualquer `LLM_MODEL`.

Importante:
- Ollama entra como **servidor de inferencia/importacao**
- o fine-tuning de pesos acontece fora do Ollama
- o treino usa um **model ID do Hugging Face**
- depois voce publica esse resultado no Ollama com um **nome de modelo do Ollama**

Exemplo:
- base de treino: `Qwen/Qwen2.5-7B-Instruct`
- nome final no Ollama: `pre-search-qwen2.5-ft-v1`

## Como isso conversa com a API

Nada muda no contrato da API.

Hoje a API envia para a LLM um payload deste tipo:

```json
{
  "message_text": "radiador gol 2010",
  "last_messages": [],
  "dictionary_seed_criteria": {
    "part_query": "radiador",
    "vehicle_model": "Gol",
    "vehicle_year": 2010
  },
  "score_policy": {
    "criteria_weights": {
      "part_code": 100,
      "part_query": 45
    },
    "min_score_to_search": 70
  }
}
```

No fine-tuning, o modelo aprende a responder melhor para esse mesmo tipo de entrada.

Depois do treino:
- a API continua mandando `system + user`
- o modelo continua respondendo em JSON
- so muda o `LLM_MODEL` apontando para a versao ajustada

## O que o exportador faz

Script:
- `scripts/training/export_pre_search_fine_tuning_dataset.py`

Ele:
- le o dataset salvo no Postgres
- recalcula `dictionary_seed_criteria`
- recalcula `score_policy`
- gera `messages.jsonl` no formato de conversa
- gera `records.jsonl` no formato canonico do projeto
- grava `system_prompt.txt` e `manifest.json`

## Como preparar o banco

Se voce for iniciar do zero:

```bash
docker compose down -v
docker compose up -d --build
```

Se o banco ja existe e voce quer reaplicar o schema consolidado:

```bash
python scripts/db/apply_sql_file.py \
  --sql-file db/init/pre_search_init.sql \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

## Como exportar os exemplos

```bash
python scripts/training/export_pre_search_fine_tuning_dataset.py \
  --dataset-slug pre-search-ft-v1 \
  --output-dir .tmp/fine_tuning \
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Saida esperada:
- `.tmp/fine_tuning/pre-search-ft-v1/train.messages.jsonl`
- `.tmp/fine_tuning/pre-search-ft-v1/validation.messages.jsonl`
- `.tmp/fine_tuning/pre-search-ft-v1/train.records.jsonl`
- `.tmp/fine_tuning/pre-search-ft-v1/validation.records.jsonl`
- `.tmp/fine_tuning/pre-search-ft-v1/system_prompt.txt`
- `.tmp/fine_tuning/pre-search-ft-v1/manifest.json`

## Exemplos seed

O schema ja sobe com exemplos iniciais, incluindo:
- `radiador gol 2010` -> `ask` por `engine`
- `radiador gol 2010 1.6` -> `search`
- `bandeja ecosport 2008` -> `ask` por `side`
- `codigo AB-1234` -> `search`
- `correia de comando gol 2010` -> `ask` e `part_code = null`
- `quero ajuda com financiamento do carro` -> `handoff`

Esses exemplos servem como norte inicial. O ideal e aumentar esse dataset com conversas reais revisadas.

## Captura de conversas reais

Quando `PRE_SEARCH_REVIEW_CAPTURE_ENABLED=true`, a API salva cada validacao do pre-search em `pre_search_review_interaction`.

Isso guarda:
- mensagem recebida
- contexto (`last_messages`)
- decisao prevista
- criteria previsto
- missing_fields previsto
- pergunta prevista
- resposta final enviada ao cliente
- modelo usado
- trilha da LLM (`llm_endpoint_used`, `llm_raw_content`, `llm_output_valid`, `llm_parse_error`, `llm_fallback_used`, `llm_decision_raw`)

Depois voce revisa os casos e informa:
- `reviewed_decision`
- `reviewed_question_key`
- `reviewed_question_prompt`
- opcionalmente `reviewed_criteria` e `reviewed_missing_fields`

CLI:

```bash
python scripts/training/review_pre_search_queue.py list --status pending --limit 20
python scripts/training/review_pre_search_queue.py review --interaction-id 12 --decision ask --question-key engine --question-prompt "Qual a motorizacao do veiculo?"
python scripts/training/review_pre_search_queue.py promote --dataset-slug pre-search-ft-v1 --split train --interaction-id 12
```

## O que treinar fora deste projeto

Este repositorio nao inclui uma stack pesada de treino. Isso foi proposital.

Motivo:
- fine-tuning exige GPU, dependencias e pipeline especificos
- o runtime da API nao deve ficar acoplado ao ambiente de treino

Entao a divisao correta e:
- este projeto: prepara dataset, versiona exemplos e consome o modelo ajustado
- stack de treino: executa o fine-tuning
- stack de inferencia: publica o modelo final

## Como o modelo treinado volta para o sistema

Depois que o treino terminar, voce publica o novo modelo no seu servidor de inferencia.

Entao ajusta o `.env`:

```env
LLM_BASE_URL=http://ollama:11434
LLM_MODEL=pre-search-qwen2.5-ft-v1
```

Se o modelo treinado estiver em outro provedor, muda tambem o `LLM_BASE_URL`.

Se voce tiver um adapter/pesos finais e quiser empacotar no Ollama:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path "C:\\caminho\\para\\adapter" \
  --base-model qwen2.5:7b
```

Se voce estiver usando o container `ollama`, rode:

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

O repositorio agora tem uma imagem separada de treino:
- `trainer/Dockerfile`
- `trainer/train_pre_search_adapter.py`

Ela:
- le `train.messages.jsonl`
- treina um adapter LoRA/QLoRA
- salva o adapter em `output-dir/adapter`
- deixa o adapter pronto para importacao no Ollama

Perfil recomendado para uso local:
- GPU NVIDIA com 16 GB de VRAM
- defaults atuais pensados para QLoRA 4-bit em 7B:
  - `TRAINER_BATCH_SIZE=1`
  - `TRAINER_GRAD_ACCUM_STEPS=8`
  - `TRAINER_MAX_SEQ_LENGTH=1024`

Se der `CUDA out of memory`, reduza primeiro:
- `TRAINER_MAX_SEQ_LENGTH=768`
- depois `TRAINER_MAX_SEQ_LENGTH=512`, se ainda necessario

Build:

```bash
docker compose --profile trainer build trainer
```

Validar GPU:

```bash
docker compose --profile trainer run --rm trainer python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"
```

Treino manual:

```bash
docker compose --profile trainer run --rm trainer \
  python trainer/train_pre_search_adapter.py \
  --train-file .tmp/fine_tuning/pre-search-ft-v1/train.messages.jsonl \
  --validation-file .tmp/fine_tuning/pre-search-ft-v1/validation.messages.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir .tmp/trainer_runs/pre-search-qwen2.5-ft-v1
```

Depois:

```bash
python scripts/training/package_pre_search_ollama_model.py \
  --model-name pre-search-qwen2.5-ft-v1 \
  --artifact-kind adapter \
  --artifact-path ".tmp\\trainer_runs\\pre-search-qwen2.5-ft-v1\\adapter" \
  --base-model qwen2.5:7b \
  --create \
  --create-via-docker
```

## Comando unico de ciclo

Script:
- `scripts/training/run_pre_search_fine_tuning_cycle.py`

Ele faz:
1. exporta o dataset do banco
2. builda e executa a Docker `trainer` por padrao
3. copia o adapter para a area montada do `ollama` e publica o modelo novo
4. compara modelo atual vs candidato no golden set
5. se o candidato ficar melhor, atualiza `LLM_MODEL`
6. opcionalmente reinicia o `docker-agent`

Fluxo recomendado na maquina com GPU:

```bash
docker compose up -d --build
docker exec ollama ollama pull qwen2.5:7b
python scripts/training/run_pre_search_fine_tuning_cycle.py --promote-if-better --restart-agent
```

Observacoes:
- se o volume do `ollama` for recriado, voce precisa puxar o modelo base de novo dentro do container
- quando `LLM_BASE_URL=http://ollama:11434`, o modelo referenciado em `LLM_MODEL` precisa existir no container `ollama`
- na primeira execucao, a `trainer` baixa o modelo base do Hugging Face
- o nome do modelo novo e gerado automaticamente por `FT_TARGET_MODEL_PREFIX`
- se o benchmark nao mostrar melhora, o `.env` nao e atualizado
- o script grava o resumo da run em `pre_search_fine_tuning_run`

Se voce ja tiver um candidato pronto no Ollama, pode pular o treino:

```bash
python scripts/training/run_pre_search_fine_tuning_cycle.py \
  --candidate-model pre-search-qwen2.5-ft-v2 \
  --promote-if-better \
  --restart-agent
```

## Recomendacao pratica para o TCC

Para sustentar bem a proposta academica:

1. use o dataset seed como baseline
2. adicione exemplos reais revisados
3. separe `train`, `validation` e `test`
4. compare:
   - modelo base
   - modelo base + few-shot
   - modelo fine-tuned
5. meca:
   - acuracia de `decision`
   - acuracia de `missing_fields`
   - taxa de `part_code` hallucinado
   - taxa de `handoff` indevido
   - latencia
