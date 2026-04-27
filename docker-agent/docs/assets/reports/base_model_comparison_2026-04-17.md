# Comparativo De Modelos Base Antes Do Fine-Tuning - 2026-04-17

## Escopo

Antes de iniciar o fine-tuning, foi executada uma comparacao entre modelos base candidatos para o runtime do pre-search.

Fluxos usados:

- bateria real do endpoint `POST /respond`
- avaliacao offline no MVP
- benchmark offline no golden set

Modelos avaliados com bateria real completa:

- `qwen2.5:7b`
- `qwen3:8b`
- `llama3.1:8b`

Modelo nao concluido:

- `gemma3:12b`

Motivo:

- latencia operacional alta demais para a bateria real de 50 casos, com casos observados em faixa de aproximadamente `185-203 s` por chamada

## Resultado Consolidado

| Modelo | MVP Decision % | MVP Slot % | MVP Next Q % | Golden Pass % | Golden Decision % | Golden Criteria % | Golden Missing % | Golden Next Q % | Golden Avg ms | Golden P95 ms | Real HTTP 200 | Real show_items | Real handoff | Real Avg ms | Real Max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `qwen2.5:7b` | 35.0 | 71.7 | 25.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 33496.07 | 37864.1 | 48 | 24 | 6 | 55237.99 | 94062.2 |
| `qwen3:8b` | 15.0 | 67.92 | 25.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 45242.11 | 49567.98 | 48 | 21 | 5 | 45987.43 | 76402.47 |
| `llama3.1:8b` | 20.0 | 67.92 | 31.25 | 84.62 | 100.0 | 100.0 | 83.33 | 84.62 | 39900.92 | 53942.87 | 48 | 20 | 6 | 43567.39 | 78733.6 |

## Leitura Tecnica

- `qwen2.5:7b`
  - baseline mais estavel no MVP offline
  - manteve `100%` no golden set
  - foi o mais lento na bateria real

- `qwen3:8b`
  - manteve `100%` no golden set
  - melhorou a latencia real em relacao ao baseline
  - reduziu `handoff` de `6` para `5`
  - caiu no MVP offline, indicando necessidade de recalibracao se a troca virar padrao

- `llama3.1:8b`
  - foi o mais rapido na bateria real
  - perdeu qualidade no golden set
  - os erros residuais apareceram principalmente em `missing_fields` e `next_question_key`

## Conclusao Provisoria

Antes do fine-tuning, o melhor equilibrio observado foi:

1. `qwen3:8b`
2. `qwen2.5:7b`
3. `llama3.1:8b`

Interpretacao:

- `qwen3:8b` apareceu como melhor candidato de troca de base no estado atual
- `qwen2.5:7b` continua sendo o baseline mais seguro
- `llama3.1:8b` e atraente em latencia, mas nao sustentou a mesma qualidade no benchmark controlado
- `gemma3:12b` nao se mostrou operacionalmente viavel no hardware e fluxo atuais

## Uso No Projeto

Este comparativo foi executado antes do fine-tuning para registrar que:

- houve avaliacao de mais de um modelo base
- a escolha do modelo inicial nao ficou baseada apenas em preferencia subjetiva
- a etapa de fine-tuning parte de uma analise previa de baseline versus alternativas reais de runtime
