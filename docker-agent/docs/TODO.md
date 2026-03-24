# TODO - Proximos Passos (docker-agent)

## Prioridade Alta

- [ ] Endurecer o criterio de liberacao para `search`
  - O threshold atual (`min_score_to_search = 70`) esta permissivo demais
  - Revisar score minimo global e/ou permitir threshold por familia de peca
  - Exigir mais contexto para pecas ambiguas antes de liberar busca
  - Validar casos como:
    - `amortecedor ecosport`
    - `coxim ecosport`
    - `pastilha corolla`
  - Evitar que `part_query + vehicle_model` sozinho libere `search` em familias que normalmente exigem mais discriminadores

- [ ] Revisar regras obrigatorias por familia de peca
  - Auditar `needs_side`, `needs_position`, `needs_axle`, `needs_engine` e `needs_variant`
  - Validar se a regra cadastrada condiz com a pergunta esperada ao usuario
  - Corrigir inconsistencias entre slot e prompt, por exemplo:
    - `side` deve significar `esquerdo/direito`
    - `position` deve significar `dianteiro/traseiro`
  - Priorizar familias com maior volume e maior ambiguidade operacional

- [ ] Melhorar a escolha da proxima pergunta
  - Quando a busca ainda nao puder ser liberada, perguntar o dado mais util para destravar `search`
  - Quando `part_query` ja estiver claro e faltar contexto do veiculo, priorizar `vehicle_model`, `vehicle_year` ou `engine`
  - Evitar perguntas vagas como "qual tipo de amortecedor?" quando o termo da peca ja esta explicito
  - Manter a futura desambiguacao por muitos resultados baseada nos candidatos retornados

- [ ] Refinar relevancia da busca ERP
  - Melhorar ranking para reduzir empates e itens excessivamente genericos
  - Penalizar familias relacionadas quando o usuario pediu uma peca mais especifica
  - Validar separacao entre:
    - `amortecedor`
    - `kit amortecedor`
    - `coxim amortecedor`
    - `batente e coifa`
  - Melhorar match exato de modelo para evitar poluicao como `COROLLA` vs `COROLLA CROSS`

## Prioridade Media

- [ ] Expandir e calibrar a pre-validacao lexical
  - A base atual ja cobre aliases curados e fuzzy conservador para `part_query`
  - Avaliar expansao para `vehicle_model` e `vehicle_brand` somente com threshold seguro
  - Medir impacto em abreviacoes, truncamentos e erros simples sem aumentar falso-positivo
  - Priorizar uso como guardrail e enriquecimento do `dictionary_seed_criteria`, sem substituir a decisao conversacional da LLM

- [ ] Pergunta inteligente de desambiguacao para muitos resultados
  - Escolher o melhor discriminador entre os itens retornados
  - Permitir configurar o threshold de "muitos resultados"
  - Priorizar perguntas que reduzam mais o conjunto de resultados com a menor friccao para o usuario

- [ ] Monitoramento de qualidade
  - Aumentar `docs/assets/datasets/pre_search_eval_dataset_mvp.json`
  - Rodar avaliacao periodica (`scripts/eval/evaluate_pre_search.py`)
  - Acompanhar cobertura por marca/modelo/peca
  - Separar metricas de:
    - liberacao correta para `search`
    - qualidade da proxima pergunta
    - qualidade do ranking ERP

- [ ] Criar rotina de carga de dados (seed incremental)
  - Definir formato de entrada (CSV/JSON)
  - Reaproveitar o bootstrap consolidado como fonte principal
  - Versionar somente seeds/init por lote de cadastro

## Prioridade Baixa

- [ ] Reavaliar a latencia residual do `pre_search_validator`
  - `LLM_KEEP_ALIVE=1h` e warmup no startup ja mitigaram o unload apos idle e a primeira chamada util
  - O modelo ainda fica lento mesmo carregado, entao a frente saiu do topo do backlog, mas nao foi zerada
  - Manter revalidacao com `scripts/eval/benchmark_pre_search_latency.py`
  - Futuras frentes: GPU no Ollama, bypass deterministico de casos obvios, duracoes detalhadas (`load_duration`, `prompt_eval_duration`, `eval_duration`) e revisao de prompt apenas se houver ganho funcional

- [ ] Definir estrategia de melhoria da decisao da LLM (`search` vs `ask`)
  - Comecar por `few-shot` e avaliacao
  - Considerar `fine-tuning` so com volume suficiente de exemplos rotulados
  - Nao usar treino como compensacao para falhas de catalogo, regras ou orquestracao

## Criterio de conclusao da fase

- [ ] Fluxo conversacional consistente entre `ask -> follow-up -> search`
- [ ] `dictionary_seed_criteria` cobrindo as familias mais frequentes do negocio
- [ ] Liberacao para `search` mais precisa, com menos falso-positivo
- [ ] Proxima pergunta mais util e menos generica
- [ ] Ranking ERP aceitavel para os casos reais priorizados
