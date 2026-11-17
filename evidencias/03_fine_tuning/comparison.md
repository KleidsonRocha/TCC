# Comparação Qwen original e fine-tuning

Estado: complete

| Conjunto | Original | Fine-tuning |
|---|---:|---:|
| Conversas por categoria | 371 | 371 |
| Casos golden | 27 | 27 |

## Categorias

| Resultado | Original | Fine-tuning |
|---|---:|---:|
| handoff_por_dado_desconhecido | 105 | 106 |
| itens_coerentes_com_cadastro | 133 | 131 |
| nao_concluiu_busca_com_itens_na_fonte | 61 | 63 |
| sem_itens_na_subcategoria_fonte | 34 | 34 |
| suspeita_falso_negativo | 34 | 34 |
| suspeita_item_incorreto | 4 | 3 |

## Métricas complementares

| Métrica | Original | Fine-tuning |
|---|---:|---:|
| Golden aprovado (todos) | 27/27 | 24/27 |
| Golden aprovado (sem coincidência exata com treino/validação) | 21/21 | 18/21 |
| Golden: decisão correta (%) | 100.0 | 88.89 |
| Golden: critérios esperados corretos (%) | 100.0 | 98.88 |
| Golden: campos faltantes esperados recuperados (%) | 100.0 | 100.0 |
| Golden: chave da próxima pergunta correta (%) | 100.0 | 88.89 |
| Categorias: turnos | 557 | 558 |
| Categorias: chamadas LLM | 80 | 80 |
| Categorias: respostas LLM cortadas em 220 tokens | 23 | 44 |
| Categorias: JSONs brutos completos | 57 | 36 |
| Categorias: erros de turno | 0 | 0 |
| Categorias: média por turno (s) | 2.9 | 3.435 |
| Categorias: mediana por turno (s) | 0.955 | 0.921 |
| Categorias: p95 por turno (s) | 15.003 | 19.402 |
| Categorias: média de turno com LLM (s) | 13.489 | 17.346 |
| Categorias: buscas | 173 | 170 |
| Categorias: conversas com filtro divergente de dado veicular conhecido | 16 | 13 |

## Alterações por caso

| Resultado original → ajustado | Casos |
|---|---:|
| handoff_por_dado_desconhecido -> handoff_por_dado_desconhecido | 105 |
| sem_itens_na_subcategoria_fonte -> sem_itens_na_subcategoria_fonte | 34 |
| suspeita_falso_negativo -> suspeita_falso_negativo | 32 |
| nao_concluiu_busca_com_itens_na_fonte -> nao_concluiu_busca_com_itens_na_fonte | 60 |
| itens_coerentes_com_cadastro -> itens_coerentes_com_cadastro | 131 |
| suspeita_item_incorreto -> nao_concluiu_busca_com_itens_na_fonte | 1 |
| itens_coerentes_com_cadastro -> suspeita_falso_negativo | 2 |
| suspeita_falso_negativo -> nao_concluiu_busca_com_itens_na_fonte | 2 |
| suspeita_item_incorreto -> suspeita_item_incorreto | 3 |
| nao_concluiu_busca_com_itens_na_fonte -> handoff_por_dado_desconhecido | 1 |

## Validação isolada e fluxo completo

Regressões do candidato no golden isolado: search_oil_viscosity_5w40, search_oil_viscosity_hyphen, search_multi_item_gate_radiador_bandeja.
Dessas regressões, os seguintes casos tiveram respostas e buscas idênticas no fluxo completo, resolvidas deterministicamente sem chamar a LLM: search_oil_viscosity_5w40, search_oil_viscosity_hyphen, search_multi_item_gate_radiador_bandeja.
Uma falha da validação isolada não deve ser descrita automaticamente como falha do atendimento completo. Os dois registros estão preservados separadamente.

## Limites

- Os dois modelos usam Transformers em BF16, com a mesma geração greedy e restrição de JSON Schema. O artefato quantizado histórico do Ollama não foi reexecutado.
- Snapshot do ERP e código do backend congelados; as referências preservam as entradas dos 371 casos originais.
- Os julgamentos por categoria são triagem de coerência com o cadastro, exigem revisão humana e não certificam encaixe físico nem recuperação de todo o estoque.
- O golden usa a pontuação existente dos campos esperados na validação isolada de pre-search; seis mensagens coincidem exatamente com o treino e são reportadas separadamente. A execução do fluxo completo é evidência distinta.
- Ausência de coincidência exata não exclui paráfrases ou modelos de conversa compartilhados com o treino.
- Uma rodada por modelo; tempos incluem SSH e backend, excluem a inspeção independente da fonte e não constituem benchmark de carga.
- O transporte pelo gateway, Redis e WhatsApp não foi exercitado.
