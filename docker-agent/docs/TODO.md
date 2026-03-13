# TODO - Proximos Passos (docker-agent)

## Prioridade Alta


- [ ] Implantar busca real de pecas (substituir mock)
  - Implementar `ToolsPort.search_parts` com integracao real (API/DB/ERP)
  - Definir estrategia de ranking (score) e filtros minimos
  - Mapear retorno real para `PartItem` (`item_id`, `title`, `score`)
  - Tratar timeout/erro da fonte externa e fallback operacional

- [ ] Remover mock de pesquisa da runtime
  - Retirar dependencia de `app/infra/tools_mock.py` no fluxo principal
  - Manter mock apenas para testes locais (quando necessario)
  - Atualizar `README` e `docs/*` para refletir busca real


## Prioridade Media

- [ ] Criar rotina de carga de dados (seed incremental)
  - Definir formato de entrada (CSV/JSON)
  - Criar script de importacao idempotente
  - Versionar somente seeds/init por lote de cadastro (sem migrations)

- [ ] Monitoramento de qualidade
  - Aumentar `docs/assets/datasets/pre_search_eval_dataset_mvp.json`
  - Rodar avaliacao periodica (`scripts/eval/evaluate_pre_search.py`)
  - Acompanhar cobertura por marca/modelo/peca

- [ ] Definir estrategia de melhoria da decisao da LLM (`search` vs `ask`)
  - `Few-shot` (contexto no prompt): enviar exemplos de entrada + decisao correta em cada chamada.
  - Efeito do `few-shot`: melhora comportamento na conversa atual, mas nao treina o modelo de forma permanente.
  - `Fine-tuning` (treino do modelo): usar dataset rotulado para ajustar pesos do modelo.
  - Efeito do `fine-tuning`: aprendizado persistente entre chamadas, com maior custo e operacao mais complexa.
  - Regra pratica: comecar por `few-shot` + avaliacao; considerar `fine-tuning` so com volume bom de exemplos rotulados.

## Criterio de conclusao da fase

- [ ] Cobertura de catalogo suficiente para reduzir misses recorrentes em producao
- [ ] `search_parts` real ativo no fluxo principal
- [ ] Mock fora da operacao normal (somente teste/dev)
