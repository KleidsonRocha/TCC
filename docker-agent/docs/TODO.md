# TODO - Proximos Passos (docker-agent)

## Prioridade Alta

- [ ] Reduzir a latencia do `pre_search_validator`
  - O gargalo atual e a chamada ao Ollama, nao a busca no ERP
  - Reduzir `LLM_NUM_PREDICT` e revisar tamanho do prompt
  - Avaliar bypass parcial da LLM quando `dictionary_seed_criteria` + `conversation_state` forem suficientes
  - Medir tempo medio por cenario: `ask`, `search` e `handoff`

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

- [ ] Melhorar a cobertura lexical do catalogo de pecas
  - Cobrir singular/plural e variacoes simples de alias antes de depender da LLM
  - Exemplos recorrentes:
    - `batente` vs `batentes`
    - `amortecedor` vs `amortecedores`
  - Priorizar termos que hoje ficam sem `dictionary_seed_criteria.part_query`
  - Tratar isso como curadoria de catalogo e nao como responsabilidade exclusiva da LLM

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

- [ ] Criar pre-validacao lexical antes da LLM
  - Avaliar uso de SQL/Postgres com `pg_trgm` para aproximacao textual de aliases e nomes de peca
  - Usar essa etapa para canonizar termos com erro de digitacao recorrente antes da chamada da LLM
  - Priorizar uso como guardrail e enriquecimento do `dictionary_seed_criteria`, sem substituir a decisao conversacional da LLM
  - Medir impacto em casos como abreviacoes, truncamentos e erros simples
  - Aplicar fuzzy apenas em campos curtos de alias/peca/codigo

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
  - Criar script de importacao idempotente
  - Versionar somente seeds/init por lote de cadastro

## Prioridade Baixa

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
