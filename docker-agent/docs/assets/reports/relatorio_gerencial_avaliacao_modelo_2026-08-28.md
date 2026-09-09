# Relatório gerencial de avaliação do assistente de autopeças

**Data:** 28/08/2026  
**Escopo:** `docker-agent`, validação pré-pesquisa e integração com o ERP  
**Modelo de referência:** `qwen2.5:7b`  

## Resumo executivo

O protótipo apresenta funcionamento consistente nos fluxos curados e estabilidade estrutural na bateria de conversas reais. A bateria omnichannel confirmou que a avaliação agora não sofre do vazamento temporal identificado na execução anterior: nenhuma resposta posterior ao turno avaliado permaneceu no contexto enviado.

O sistema já consegue extrair mais de uma peça em uma mesma mensagem e registrar essa informação em `items[]`. Entretanto, a interpretação de conversas comerciais reais ainda apresenta limitações em troca de veículo, peças compostas, pendências multi-item e distinção entre intenção do cliente e campo solicitado.

O principal risco operacional continua sendo a latência do caminho que depende da LLM. A mediana da bateria real foi de aproximadamente 36,4 segundos, embora os caminhos determinísticos permaneçam significativamente mais rápidos.

**Classificação gerencial atual:** protótipo funcional, adequado para demonstração controlada e evolução; ainda não recomendado para atendimento comercial autônomo.

## Conjuntos avaliados

### Teste curado

Arquivo: `battery_structural_respond_v2.json`

O conjunto curado verifica comportamentos objetivos e reproduzíveis, como:

- decisões `search`, `ask` e `handoff`;
- campos extraídos e normalizados;
- perguntas obrigatórias;
- caminhos determinísticos;
- proveniência de códigos;
- desambiguação e estado multi-turno;
- regressões conhecidas.

Resultado registrado no projeto: **187 testes aprovados**.

Esse conjunto é o principal indicador de conformidade funcional do contrato e das regras do backend.

### Teste real omnichannel

Arquivo: `battery_real_omnichannel_250.json`  
Execução analisada: `real_respond_battery_agent_20260828T130959729829Z.json`

O dataset contém 250 cenários reais selecionados de conversas omnichannel. Nesta execução foi usado o nível `smoke`, com 30 cenários e 65 turnos.

## Resultados quantitativos

| Indicador | Resultado |
|---|---:|
| Turnos executados | 65 |
| Respostas HTTP 200 | 65 |
| Assertion failures | 0 |
| Vazamento de resposta futura após o turno atual | 0 |
| Mediana de latência | 36,4 s |
| Média de latência | 28,9 s |
| P95 de latência | 55,9 s |
| Pior caso | 65,9 s |
| Chamadas pelo caminho LLM | 43 |
| `deterministic_ask` | 12 |
| `deterministic_bypass` | 6 |
| `result_disambiguation` | 4 |

Os `0 assertion failures` da bateria real não devem ser interpretados como 100% de acerto. A maior parte dos cenários omnichannel ainda possui expectativa estrutural de HTTP 200, aguardando validação comercial humana para critérios semânticos.

## Comparação com a execução anterior

| Indicador | Execução anterior | Execução atual |
|---|---:|---:|
| Respostas futuras vazadas no contexto | 65 | 0 |
| Mediana | 32,6 s | 36,4 s |
| Pior caso | 95,6 s | 65,9 s |
| Chamadas LLM | 44 | 43 |
| Turnos acima de 30 s | 38 | 41 |

A validade metodológica melhorou claramente. A latência máxima caiu, mas a mediana e a quantidade de casos acima de 30 segundos ainda exigem atenção.

## Evidências funcionais positivas

- O contexto futuro foi removido corretamente do runner.
- A mensagem atual passou a ter precedência sobre valores antigos e respostas conflitantes da LLM.
- `side`, `position` e `axle` passaram a ser tratados como dimensões distintas.
- O sistema identificou múltiplas peças em mensagens reais e registrou-as em `items[]`.
- Quantidades passaram a exigir evidência linguística explícita.
- A resposta conservadora de handoff foi preservada para famílias fora do catálogo.
- A ausência de resultado no ERP continua não sendo comunicada como incompatibilidade veicular.

## Limitações observadas

Os casos reais ainda revelaram problemas relevantes:

- troca de veículo pode não substituir completamente o contexto anterior;
- uma resposta do cliente que não atende à pergunta pendente pode fazer o sistema repetir a pergunta;
- peças compostas ainda podem ser reduzidas à família principal incorreta;
- `items[]` já é extraído, mas a validação comercial de cada item ainda precisa ser ampliada;
- a bateria smoke ainda não exercitou uma quantidade suficiente de respostas `item_results` agregadas;
- casos multi-item ainda precisam de `active_item_index` para completar uma peça específica sem perder as demais;
- a latência residual da LLM continua alta para atendimento em tempo real.

## Interpretação gerencial

O resultado mostra que a arquitetura é viável, mas que o principal desafio deixou de ser apenas consultar o ERP. A dificuldade central agora é interpretar corretamente uma conversa comercial real, manter o contexto e decompor pedidos complexos em itens independentes.

O sistema está em condições de:

- demonstrar o fluxo completo em ambiente controlado;
- apoiar atendimento humano;
- coletar dados para regressão e melhoria;
- sustentar a avaliação acadêmica da arquitetura.

Ainda não está em condições de:

- operar sem supervisão em pedidos complexos;
- afirmar compatibilidade apenas com base em ausência de resultado;
- garantir orçamento completo para mensagens com várias peças;
- cumprir uma meta de atendimento instantâneo nos casos que exigem LLM.

## Próximas prioridades

1. Criar expectativas comerciais revisadas para os casos reais prioritários.
2. Adicionar regressões específicas para troca de veículo e resposta espontânea.
3. Implementar `active_item_index` para pendências por item.
4. Validar a resposta `item_results` em cenários reais com duas ou mais peças.
5. Corrigir a taxonomia das peças compostas diretamente no catálogo quando necessário.
6. Medir e reduzir a cauda de latência do caminho LLM após as correções funcionais.

## Conclusão

O protótipo demonstrou funcionamento técnico e evolução mensurável na qualidade da avaliação. O teste curado indica conformidade com os comportamentos estruturais definidos, enquanto o teste real omnichannel revelou os limites de interpretação que ainda precisam ser tratados.

O resultado mais importante não é afirmar que todas as conversas foram resolvidas, mas demonstrar de forma reproduzível onde o sistema funciona, onde falha e quais melhorias produzem impacto. Isso caracteriza um estágio adequado para demonstração e continuidade do TCC, mas ainda anterior à operação comercial autônoma.
