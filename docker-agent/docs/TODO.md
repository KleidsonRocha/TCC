# TODO - Proximos Passos (docker-agent)

## Prioridade Alta

- [ ] Ampliar cobertura do catalogo em banco (pre-search)
  - Cadastrar mais `brands`, `models`, `model_aliases`, `part_types` e `part_aliases`
  - Revisar `pre_search_part_rule` para `is_generic`, `needs_engine`, `needs_side`, `needs_position`
  - Cadastrar mais `pre_search_engine_option` por modelo/faixa de ano
  - Incluir erros comuns de digitacao em aliases

- [ ] Implantar busca real de pecas (substituir mock)
  - Implementar `ToolsPort.search_parts` com integracao real (API/DB/ERP)
  - Definir estrategia de ranking (score) e filtros minimos
  - Mapear retorno real para `PartItem` (`item_id`, `title`, `score`)
  - Tratar timeout/erro da fonte externa e fallback operacional

- [ ] Remover mock de pesquisa da runtime
  - Retirar dependencia de `app/infra/tools_mock.py` no fluxo principal
  - Manter mock apenas para testes locais (quando necessario)
  - Atualizar `README` e `docs/*` para refletir busca real

- [ ] Implementar validacao por score ponderado (pre-search)
  - Definir pesos por criterio: `part_code`, `part_query`, `vehicle_brand`, `vehicle_model`, `vehicle_year`, `engine`, `side`, `position`
  - Definir `score_minimo` para liberar `search`
  - Regra de corte: `part_code` valido pode liberar busca direta (override)
  - Persistir configuracao em banco (tabela de pesos e limiares) para ajuste sem deploy
  - Em `score` abaixo do minimo: perguntar o slot faltante de maior impacto

## Prioridade Media

- [ ] Criar rotina de carga de dados (seed incremental)
  - Definir formato de entrada (CSV/JSON)
  - Criar script de importacao idempotente
  - Versionar seeds/migrations por lote de cadastro

- [ ] Monitoramento de qualidade
  - Aumentar `docs/pre_search_eval_dataset_mvp.json`
  - Rodar avaliacao periodica (`scripts/evaluate_pre_search.py`)
  - Acompanhar cobertura por marca/modelo/peca

## Criterio de conclusao da fase

- [ ] Cobertura de catalogo suficiente para reduzir misses recorrentes em producao
- [ ] `search_parts` real ativo no fluxo principal
- [ ] Mock fora da operacao normal (somente teste/dev)
