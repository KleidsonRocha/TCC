# Progresso Do Projeto

Este documento consolida o estado atual do projeto sem depender de leitura fragmentada de relatorios e arquivos historicos.

## O Que Ja Esta Implementado

- API `POST /respond` e `GET /health`
- extracao deterministica com catalogo em Postgres
- validacao com LLM via Ollama
- gate backend para decidir entre `ask`, `search` e `handoff`
- bloqueio defensivo de `part_code` sem proveniencia literal ou validada pelo extractor
- regras direcionais de filtros corrigidas no catalogo bootstrapado
- bypass deterministico seguro para pedidos completos e follow-ups simples
- `ask` deterministico para incompletude obvia, com rollback independente
- telemetria de latencia por etapa e identificacao do caminho de pre-busca
- busca real no ERP
- captura de interacoes reais para revisao
- dataset curado para fine-tuning
- pipeline de exportacao, treino e publicacao de adapter

## Correcoes Concluidas Em 13/07/2026

### `part_code` inventado

O problema de `part_code` inventado foi solucionado:

- o caso real `pastilha de freio 2010 1.0` nao gera mais `FREIO-2010`
- a origem era o regex que aceitava `freio 2010` como codigo e o normalizava para `FREIO-2010`
- agora o codigo exige evidencia literal na mensagem ou no historico do usuario, ou validacao pelo extractor
- um `part_code` contaminado nao e mais restaurado apenas pelo `conversation_state`
- foram adicionadas regressoes para o caso real, estado contaminado e formatos validos de codigo
- a validacao final no ambiente Docker oficial encerrou com `136 passed`

### Regras de catalogo de filtros

As perguntas direcionais sem sentido para filtros foram corrigidas na fonte de verdade do bootstrap:

- `filtro de oleo` e `filtro de ar do motor` ficaram protegidos contra regressao de `needs_axle`
- `filtro de combustivel` nao exige mais `needs_side`
- a auditoria cobriu tambem filtro de ar condicionado, filtro de cabine, filtro de cambio, mangueiras de filtro de ar e pre-filtro de injecao
- foram removidos `needs_side` de mangueiras de filtro de ar e `needs_side + needs_axle` de pre-filtro de injecao
- os overrides de filtros foram retirados do runtime para o CSV bootstrapado voltar a governar essas regras
- um Postgres descartavel confirmou os oito registros carregados pelo bootstrap
- a suite completa no ambiente Docker oficial encerrou com `148 passed`

## Prioridade 1 Concluida Em 14/07/2026

### Bypass deterministico e latencia por etapa

- pedidos com alias exato ou `part_code` literal, criterios completos, requisitos do catalogo e score suficiente podem seguir direto para `search`
- follow-ups simples so usam o bypass quando respondem exatamente ao `pending_slot` de um estado anterior com `last_decision = ask`
- casos incompletos, fuzzy-only, genericos, motor textual ou estado incerto continuam usando a LLM
- o caminho e reversivel por `PRE_SEARCH_DETERMINISTIC_BYPASS_ENABLED=false`
- `tool_trace.stage_latency_ms` separa `pre_search_validator`, `search_parts` e `response_assembly`
- `tool_trace.pre_search_path` diferencia `deterministic_bypass` de `llm`
- o benchmark de latencia agora executa e compara explicitamente os dois caminhos

Medicao real antes/depois no mesmo ambiente:

- `radiador gol 2010 1.0`: `71668.38 ms -> 1313.73 ms`, reducao de `98.2%`
- follow-up `1.0` para motor pendente: `46730.79 ms -> 926.96 ms`, reducao de `98.0%`
- no pedido completo otimizado, as etapas internas foram `362.70 ms` de pre-busca, `860.38 ms` de ERP e `0.11 ms` de montagem
- no follow-up otimizado, foram `589.55 ms` de pre-busca, `284.44 ms` de ERP e `0.09 ms` de montagem

Reavaliacao de infraestrutura:

- o Ollama esta inferindo em CPU (`size_vram = 0`)
- `LLM_KEEP_ALIVE=1h` ja estava ativo e o modelo permanecia carregado, portanto nao era o gargalo principal
- GPU permanece recomendada para reduzir a latencia dos casos complexos que ainda exigem LLM
- keep-alive e prompt foram preservados ate existir benchmark que demonstre ganho adicional de tempo ou qualidade
- a suite completa no ambiente Docker oficial encerrou com `159 passed`

## Prioridade 0 Concluida Em 27/08/2026

### Contrato e runtime do `deterministic_ask`

- a elegibilidade do bypass de `ask` foi isolada em uma politica pura e conectada ao runtime antes da LLM
- familia conhecida so e aceita quando o alias aparece de forma exata na mensagem atual; fuzzy isolado nao confirma `part_query`
- pedido sem familia so e aceito quando solicita explicitamente uma peca ou item automotivo, como `quero uma peca`
- os campos ausentes e a pergunta seguinte continuam sendo calculados pelas regras e templates do backend
- a prioridade entre campos ausentes ficou fixa em `part_query`, modelo, ano, motor, lado, posicao, eixo e variante
- descricao funcional, sintoma, mudanca de assunto, intencao de handoff, `part_code`, candidato nao resolvido e estado com slot pendente permanecem fora desse caminho
- o resultado usa o mesmo `PreSearchValidation`, `NextQuestion` e `ConversationState` ja devolvidos ao `docker-comm`, sem alterar o contrato persistido no Redis
- qualquer inelegibilidade, retorno invalido ou excecao cai imediatamente no caminho da LLM
- o bypass e independente do bypass de `search` e pode ser revertido por `PRE_SEARCH_DETERMINISTIC_ASK_ENABLED=false`
- `tool_trace.pre_search_path` identifica o novo caminho como `deterministic_ask`
- foram adicionadas 28 regressoes entre contrato e integracao; `tests/test_rules.py` encerrou com `91 passed`
- a suite completa no container Linux oficial encerrou com `187 passed in 31.70s`

Medicao real antes/depois com 50 casos em cada modo:

- chamadas a LLM: `31 -> 12`, reducao de `61,3%`
- 19 casos migraram de `llm` para `deterministic_ask`
- nesses 19 casos, a media caiu de `35.325,42 ms` para `721,21 ms`, reducao de aproximadamente `97,96%`
- latencia media global: `23.150,87 ms -> 10.836,37 ms`, reducao de `53,19%`
- p50 global: `31.410,35 ms -> 741,96 ms`, reducao de `97,64%`
- p95 global: `42.939,14 ms -> 43.902,60 ms`; a cauda residual da LLM em CPU nao melhorou
- nao houve diferenca funcional central em status, resultado, handoff, `question_key`, criterios normalizados ou `pending_slot`
- cinco perguntas de motor passaram a incluir opcoes governadas pelo catalogo que a LLM havia omitido
- evidencia consolidada em `docs/assets/reports/deterministic_ask_comparison_2026-08-27.md`

Achado de ambiente:

- o volume Postgres ativo ainda possui `filtro de combustivel -> needs_side=true`, divergindo do bootstrap versionado; a regra precisa ser reconciliada no ambiente antes do beta sem apagar dados dinamicos

## O Que Ja Esta Organizado No Banco

- catalogo deterministico e regras no bootstrap consolidado
- fila de revisao em `pre_search_review_interaction`
- dataset formal de treino em:
  - `pre_search_fine_tuning_dataset_header`
  - `pre_search_fine_tuning_dataset_record`
- historico de runs em `pre_search_fine_tuning_run`

## Evidencias Atuais

- testes automatizados em `tests/`
- datasets de avaliacao em `docs/assets/datasets/`
- relatorios de analise em `docs/assets/reports/`

Artefatos de referencia atuais:

- `docs/assets/reports/real_respond_battery_2026-03-25.md`
- `docs/assets/reports/product_owner_analysis_real_battery_2026-03-26.md`
- `docs/assets/reports/pre_search_review_interaction_first_pass_2026-04-15.md`
- `docs/assets/reports/base_model_comparison_2026-04-17.md`

## Comparativo De Modelos Base Antes Do Fine-Tuning

Ja foi executada uma comparacao entre modelos base de runtime antes do primeiro fine-tuning:

- `qwen2.5:7b`
- `qwen3:8b`
- `llama3.1:8b`
- tentativa de `gemma3:12b`, interrompida por inviabilidade operacional

Leitura consolidada:

- `qwen3:8b` apareceu como melhor candidato de equilibrio entre qualidade e latencia
- `qwen2.5:7b` permaneceu como baseline mais seguro
- `llama3.1:8b` foi mais rapido, mas perdeu qualidade no golden set
- `gemma3:12b` nao fechou a bateria real em tempo operacional aceitavel

Esse comparativo foi registrado para deixar explicito que a escolha do modelo base nao ficou restrita a um unico candidato antes da etapa de fine-tuning.

## Estado Atual Do Fine-Tuning

- o fluxo de revisao e promocao ja existe
- o dataset supervisionado ja pode ser exportado para `JSONL`
- o trainer ja esta preparado para `LoRA/QLoRA`
- a etapa mais sensivel para reproducao continua sendo:
  - estado do banco com dados dinamicos
  - disponibilidade de GPU compativel para treino

## Maiores Pendencias Atuais

As pendencias mais importantes continuam no backlog em `TODO.md`, principalmente:

- medir cobertura e ganho real do `ask` deterministico
- corrigir motor textual, `no_match` e desambiguacao multi-turno
- refinar ranking e apresentacao dos resultados do ERP
- avaliar recuperacao semantica controlada para descricoes genericas

## Proxima Fase Recomendada

1. Medir cobertura, latencia e qualidade do bypass de `ask` deterministico
2. Corrigir os fluxos conversacionais pendentes e transformar casos reais em regressao
3. Refinar ranking do ERP e reexecutar a bateria correspondente
4. Fazer prova de conceito semantica em memoria com confirmacao por template
5. Medir o volume residual de LLM antes de decidir GPU, modelo menor ou fine-tuning

## Como Manter Este Documento Util

Atualize este arquivo quando houver:

- mudanca relevante de arquitetura
- novo bloco concluido do backlog
- novo artefato importante de avaliacao
- validacao de reproducao em outro ambiente
