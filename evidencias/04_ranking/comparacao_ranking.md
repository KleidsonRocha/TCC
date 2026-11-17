# Avaliação de ranking real

Execução: `real_respond_battery_comm_20260929T125748400473Z.json`
Rótulos avaliáveis: 30; pendentes/não avaliáveis: 93; sem execução correspondente: 0.

| Métrica | Resultado |
|---|---:|
| Compatibilidade Top-1 | 28/30 (93.3%) |
| Compatibilidade Top-3 | 28/30 (93.3%) |
| Preferido/confirmado Top-1, aceitando grupos de empate | 5/7 (71.4%) |
| Candidatos incompatíveis entre posições Top-3 rotuladas | 4/76 (5.3%) |

## No-match

TP=17, FP=2, FN=3, TN=28
Precisão=89.5%; recall=85.0%.

Top-1/Top-3 contam como acerto quando o código retornado pertence a `compatible_item_ids`. `preferred_or_confirmed_item_ids` mede separadamente a preferência/seleção comercial. Grupos de empate só ampliam essa segunda métrica; eles não tornam um código compatível sem anotação explícita.


## Comparação pareada

Base: `bateria_ranking_atual.json`; atual: `real_respond_battery_comm_20260929T125748400473Z.json`; casos com chave nos dois runs: 120.

| Métrica | Base | Atual | Variação |
|---|---:|---:|---:|
| Top-1 compatível | 28/30 (93.3%) | 28/30 (93.3%) | +0.0 p.p. |
| Top-3 compatível | 28/30 (93.3%) | 28/30 (93.3%) | +0.0 p.p. |

