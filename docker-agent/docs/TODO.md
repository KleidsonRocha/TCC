# TODO - Prioridades Reais Do Produto (docker-agent)

## Base desta priorizacao

Este backlog foi reordenado a partir de:

- `docs/assets/reports/real_respond_battery_2026-03-25.json`
- `docs/assets/reports/product_owner_analysis_real_battery_2026-03-26.md`

Criterio de ordenacao:

- primeiro, corrigir o que mais afeta confianca
- depois, corrigir o que mais afeta fluidez operacional
- so entao expandir cobertura, treino e automacoes secundarias

## Prioridade 0 - Parar erros com conviccao

- [ ] Canonizar `part_query` final antes de aplicar regras e antes de montar a busca
  - Garantir que o valor final sempre caia em uma familia canonica do catalogo
  - Cobrir casos como `disco de freio` -> `discos de freio`
  - Cobrir casos como `pstilhas` -> `pastilhas de freio`
  - Tratar familias nao catalogadas, como `farol`, sem deixar passar direto para `search`

- [ ] Bloquear qualquer `part_code` inventado
  - Encontrar a origem do caso real `FREIO-2010`
  - So aceitar `part_code` literal da mensagem, do contexto ou validado pelo extractor
  - Criar regressao especifica para `pastilha de freio 2010 1.0`

- [ ] Revisar regras de catalogo que geram perguntas sem sentido
  - Corrigir `filtro de  oleo -> needs_axle`
  - Corrigir `filtro de ar do motor -> needs_axle`
  - Corrigir `filtro de combustivel -> needs_side`
  - Auditar familias similares antes da proxima bateria real

- [ ] Endurecer a liberacao para `search`
  - Recalibrar `min_score_to_search`
  - Permitir threshold por familia, se necessario
  - Impedir que `part_query + vehicle_model` sozinho libere busca em familias ambiguas
  - Garantir que `needs_engine`, `needs_side`, `needs_position`, `needs_axle` e `needs_variant` prevalecam sobre a decisao otimista da LLM

## Prioridade 1 - Trazer a latencia para nivel operacional

- [ ] Criar caminho deterministico para casos obvios
  - Bypass da LLM quando extractor + catalogo + regras ja forem suficientes
  - Priorizar pedidos completos e follow-ups simples
  - Priorizar reducao de latencia nos fluxos mais comuns da bateria real

- [ ] Medir latencia por etapa
  - Separar `pre_search_validator`, `search_parts` e montagem de resposta
  - Identificar claramente onde esta o maior custo real
  - Manter comparacao antes e depois dos bypasses

- [ ] Reavaliar infraestrutura somente depois do bypass
  - GPU no Ollama
  - ajustes de `LLM_KEEP_ALIVE`
  - revisao de prompt somente se trouxer ganho real de tempo ou qualidade

## Prioridade 2 - Fazer a conversa ficar coerente ate o fim

- [ ] Corrigir follow-up com motor textual
  - Aceitar `zetec rocam`, `duratec`, `sigma` e equivalentes textuais como `engine`
  - Revalidar explicitamente o fluxo `coxim amortecedor ecosport 2008 -> zetec rocam`

- [ ] Melhorar a resposta de `no_match`
  - Usar `conversation_state` para dizer o que realmente falta ou conflitou
  - Nao pedir novamente dados que o usuario ja informou
  - Separar `nao encontrei nada` de `sua informacao ainda esta insuficiente`

- [ ] Criar desambiguacao real quando houver muitos itens
  - Em vez de apenas listar itens, perguntar o melhor discriminador seguinte
  - Exemplos: `com ou sem ar`, `aro`, `lado`, `dianteiro ou traseiro`
  - Tratar `result_disambiguation` como etapa funcional, nao so estado salvo

- [ ] Revisar consistencia dos prompts
  - `side` deve significar `esquerdo/direito`
  - `position` deve significar `dianteiro/traseiro`
  - `axle` so deve ser usado quando fizer sentido no dominio
  - Manter perguntas curtas, diretas e especificas

## Prioridade 3 - Melhorar a qualidade da busca

- [ ] Refinar ranking do ERP
  - Penalizar itens correlatos quando o usuario pediu a peca principal
  - Reduzir ruido de `tampa`, `mangueira`, `kit`, `parafuso`, `lampada` e similares
  - Reduzir empates de score
  - Priorizar aplicacao exata sobre familia apenas relacionada

- [ ] Corrigir normalizacao de texto e encoding
  - Eliminar saidas quebradas como `veiculo`, `oleo` e `automatico` com encoding ruim
  - Garantir titulos legiveis nas listas retornadas

- [ ] Expandir a pre-validacao lexical com seguranca
  - Melhorar cobertura de typos e abreviacoes sem aumentar falso positivo
  - Priorizar `part_query`, `vehicle_model` e motor textual

## Prioridade 4 - Fechar o ciclo de qualidade com evidencias reais

- [ ] Reexecutar a bateria real apos cada bloco critico
  - bloco 1: canonizacao + `part_code` + regras de catalogo
  - bloco 2: motor textual + `no_match` + desambiguacao
  - bloco 3: ranking + latencia

- [ ] Transformar erros reais em regressao automatizada
  - Destacar pelo menos:
  - `filtro de oleo gol 2010`
  - `filtro ar motor gol 2010`
  - `filtro de combustivel gol 2010`
  - `coxim amortecedor ecosport 2008 -> zetec rocam`
  - `pastilha de freio 2010 1.0`
  - `pstilhas gol 2010`
  - `farol gol 2010`

- [ ] Consolidar os artefatos finais de avaliacao
  - manter bateria real como evidencia principal
  - manter relatorio consolidado como leitura executiva
  - manter este backlog alinhado com os achados reais

## Fora do topo agora

- [ ] Fine-tuning da LLM
  - Nao usar treino como solucao primaria para erro de catalogo, ranking ou orquestracao

- [ ] Seed incremental e rotinas de carga
  - Importante, mas nao antes de corrigir as falhas que ja apareceram na bateria real

- [ ] Benchmarks isolados que nao mudem decisao de produto
  - Manter como diagnostico, nao como foco principal

## Criterio de conclusao desta fase

- [ ] Nenhuma pergunta absurda em familias comuns de filtro, farol, freio, radiador e bandeja
- [ ] `part_query` sempre canonico antes de aplicar regras
- [ ] Nenhum `part_code` inventado na bateria real
- [ ] Follow-up textual de motor funcionando
- [ ] `show_items` acompanhado de refinamento util quando necessario
- [ ] `no_match` contextual e sem regressao de contexto
- [ ] Ranking aceitavel nos casos reais priorizados
- [ ] Latencia `p50 <= 15s`
- [ ] Latencia `p95 <= 25s`
