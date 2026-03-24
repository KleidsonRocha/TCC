# Relatorio De Latencia E Prompt - 2026-03-24

## Escopo

- implementar `keep_alive=1h` no payload do Ollama
- adicionar warmup no startup para evitar penalizar a primeira chamada util
- medir o custo do prompt atual sem alterar o prompt
- confirmar que nao houve regressao funcional

## Validacao Funcional

- suite focada: `46 passed`
- suite completa: `73 passed`

Conclusao:
- `keep_alive` e warmup nao introduziram regressao funcional nos testes do projeto

## Resultado Do `keep_alive`

### Antes Do `keep_alive`

Fonte:
- `docs/assets/reports/pre_search_validator_latency_report_2026-03-24.json`

Achados principais:
- apos `30s` de idle, o modelo ainda estava carregado e o tempo ficou em `34.5s` no cenario `ask_minimal`
- apos `330s` de idle, o modelo saiu do `/api/ps` e o tempo subiu para `98.0s` em `ask_minimal`
- apos `330s` de idle, o tempo subiu para `149.5s` no cenario `search_complete`

Leitura:
- havia regressao clara de latencia por unload do modelo apos idle

### Depois Do `keep_alive=1h`

Fonte:
- `docs/assets/reports/pre_search_validator_latency_keep_alive_2026-03-24.json`

Achados principais:
- o primeiro request ainda ficou caro quando o modelo comecou descarregado:
  - `ask_minimal`: `113.8s`
- isso mostra que `keep_alive` nao resolve cold boot inicial
- porem, apos o modelo estar carregado, o comportamento apos `330s` de idle estabilizou:
  - `ask_minimal`: media `40.5s`
  - `search_complete`: media `56.3s`
- nos dois cenarios de idle, `target_loaded_before_all=true`

Leitura:
- `keep_alive=1h` resolveu o problema de degradacao apos idle

## Resultado Do Warmup

Smoke real executado:
- warmup manual contra Ollama finalizado em aproximadamente `144 ms`
- o modelo permaneceu listado no `/api/ps` antes e depois do warmup

Leitura:
- o warmup e barato quando o modelo ja esta carregado
- ele deve ajudar a transferir o custo do primeiro carregamento para o startup da aplicacao

## Analise Do Prompt Atual

Fonte:
- `docs/assets/reports/pre_search_prompt_profile_2026-03-24.json`

Achados principais:
- o payload total ficou entre `4442` e `4633` caracteres
- o bloco fixo do system prompt ficou em `2026` caracteres
- o `prompt_eval_count` ficou entre `685` e `750`
- porem o custo de `prompt_eval_duration` foi baixo:
  - `ask_minimal`: `336.77 ms`
  - `search_complete`: `487.77 ms`
  - `follow_up_engine`: `348.05 ms`
  - `handoff_request`: `293.84 ms`
- o peso dominante ficou em `eval_duration`:
  - entre `90.14%` e `91.65%` do tempo total
- o `prompt_eval_share_pct` ficou entre `0.95%` e `1.91%`

Leitura:
- a revisao de prompt pode melhorar clareza e manutencao
- mas, para latencia pura, o ganho esperado parece pequeno
- o gargalo atual nao esta no tamanho do prompt; esta na geracao do modelo

## Veredito

- implementar `keep_alive=1h` valeu a pena
- warmup tambem vale a pena
- revisar prompt agora, pensando apenas em performance, nao parece ter ROI alto
- revisar prompt ainda pode valer por qualidade e robustez, mas nao porque ele seja hoje o principal gargalo de tempo

## Outras Recomendacoes De Performance

1. Validar se o Ollama esta usando GPU. Nos relatorios atuais aparece `size_vram: 0`, o que sugere execucao sem uso efetivo de VRAM.
2. Criar bypass deterministico para casos em que `dictionary_seed_criteria` e regras ja bastem para decidir `ask` sem chamar a LLM.
3. Registrar `load_duration`, `prompt_eval_duration` e `eval_duration` no audit recorrente, para separar claramente gargalo de carga versus gargalo de geracao.
4. Revisar se o modelo `qwen2.5:7b` e a melhor troca entre qualidade e latencia para este fluxo especifico, sem depender de reduzir `num_predict`.
5. Reduzir o volume de chamadas desnecessarias da LLM em follow-ups obvios, aproveitando melhor `conversation_state`.

## Ordem Recomendada

1. manter `keep_alive=1h`
2. manter warmup no startup
3. verificar GPU / aceleração do Ollama
4. estudar bypass deterministico antes de uma revisao grande de prompt
