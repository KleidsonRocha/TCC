# Respostas aos três apontamentos metodológicos do TCC

Adendo de 27/10/2026 — revisão recebida e informações complementares do autor.

## O que podemos responder no TCC

Sim: os três apontamentos podem receber uma resposta documental sustentada por evidências. Isso não exige afirmar que todas as limitações foram eliminadas. A ablação e a execução consolidada foram realizadas; a revisão técnica foi ampliada com a conferência integral de 371 casos por dois profissionais, conforme informação do autor. A generalização para clientes/catálogo completo e a independência estrita de avaliação continuam delimitadas.

| Apontamento | Resposta sustentada | Limite que deve permanecer |
| --- | --- | --- |
| 1. Participação incremental da LLM | Respondido por comparação pareada D/H: mesma base determinística e fonte, com três repetições. D encaminha no ponto residual; H usa o Qwen base e as validações existentes. | O efeito vale para essa política D e para o ramo híbrido completo; não prova superioridade comercial geral ou contribuição exclusivamente linguística. |
| 2. Validação comercial limitada a um avaliador | Ampliada: o autor confirmou dois profissionais, com 10 anos em vendas e 7 em aplicação de peças, ambos conferindo os 371 casos. | Não foi documentado procedimento cego, avaliação individual independente ou vínculo de cada escore exportado com cada profissional. O catálogo e a amostra continuam delimitados. |
| 3. Falta de avaliação consolidada e repetições | Consolidação técnica realizada na versão congelada 52e4d74: 3.408 execuções e três repetições, com fontes, parâmetros, saídas e falhas preservados. | A bateria foi usada no desenvolvimento das regras. Dez cenários sintéticos pós-exposição, ainda não executados, não substituem um teste prospectivo independente. |

## Texto pronto — metodologia e participação da LLM

Para examinar a participação do componente de linguagem, foi realizado um experimento pareado entre duas configurações da mesma arquitetura. A condição D manteve os caminhos determinísticos existentes e adotou encaminhamento humano conservador quando o processamento atingia o ponto residual de inferência. A condição H utilizou esses caminhos e acrescentou a inferência do Qwen2.5:7b, em formato Q4_K_M, seguida das validações e coerções existentes no backend. Foram mantidos os mesmos dados e regras, com execução local em CPU, três repetições por caso e ordem das configurações contrabalançada. Essa comparação mede a contribuição operacional do ramo híbrido em relação à política conservadora adotada, sem representar a melhor implementação determinística teoricamente possível.

Na bateria por categoria/subcategoria, a condição H acionou o modelo em 45 dos 371 casos (12,1%), enquanto 326 conversas apresentaram a mesma assinatura de conteúdo em D e H. Houve apresentação de produtos em 165 casos na condição D e em 172 na condição H. Os sete identificadores com apresentação adicional correspondem a seis pedidos iniciais distintos, devido a uma duplicação textual. Esses resultados evidenciam participação residual e aumento localizado de autonomia, mas não demonstram, por si, superioridade comercial geral. A classificação de compatibilidade cadastral de um primeiro candidato também não garante adequação da lista inteira ou da composição do pedido.

A condição H inclui a geração do modelo e as regras que interpretam, validam ou reparam sua proposta. Portanto, os efeitos observados não foram atribuídos integralmente a raciocínio autônomo da LLM. A análise manteve separados os caminhos determinísticos, as inferências efetivas, os encaminhamentos, as conversas sem conclusão na simulação e as apresentações de produtos.

## Texto pronto — revisão dos resultados por profissionais

A avaliação complementar contou com a conferência integral dos 371 casos por dois profissionais com experiência prática no domínio: um especialista em vendas de autopeças, com dez anos de experiência, e um profissional de aplicação de peças, com sete anos. Essa participação ampliou a revisão anteriormente restrita a um avaliador e incorporou perspectivas comerciais e de aplicação. Os casos analisados pertencem à bateria comparativa D/H e não constituem uma amostra aleatória de atendimentos reais.

Para organizar a inspeção das saídas, foram consideradas três dimensões analíticas — balcão, aplicação e auditoria — com apoio de verificações e classificações automatizadas. Essas dimensões não representam três profissionais independentes. Os resultados por rubrica foram tratados como descrição exploratória e complementados pela conferência profissional informada. Não se atribuiu confiabilidade interavaliadores à concordância entre as rubricas computacionais, nem se afirmou avaliação cega ou adjudicação formal sem registros desse procedimento.

A revisão preservou classificações parciais e indeterminadas e distinguiu identidade da peça, composição, aplicação registrada, necessidade das perguntas e adequação do encaminhamento. A fonte utilizada foi o snapshot exportado em 19/10/2026, com 52.798 produtos e 1.779.443 aplicações. A verificação de registros no mesmo vínculo de aplicação aumenta a rastreabilidade cadastral, mas não substitui inspeção física, catálogo técnico do fabricante ou comprovação de preço e estoque. A análise amplia a evidência no cenário estudado sem autorizar generalização a todos os produtos, veículos ou clientes.

## Texto pronto — versão congelada, repetições e limitações de independência

A versão executável foi congelada no commit 52e4d7460009d9635445c8ca69c604488b5dacef, com preservação dos arquivos, parâmetros e fonte. Foram executados 371 casos de categorias, 170 cenários estruturais e 27 casos golden, em duas condições e três repetições, totalizando 3.408 registros de caso e 4.695 turnos. As 294 chamadas de inferência registradas nos casos concluídos ocorreram em H; D não realizou inferência. Os controles adicionais arquivados registraram 604 testes do agente e 33 do gateway aprovados. A estabilidade observada nas três repetições não foi interpretada como aumento do número de clientes independentes ou como prova de correção comercial.

A execução teve dois segmentos, entre 26 e 27/10/2026, devido a uma interrupção do ambiente Docker. Foram retomados apenas os casos incompletos, preservando 1.809 registros já concluídos, com conferência do catálogo e do modelo e reaquecimento excluído das métricas. A análise documentou o par de comparação que atravessou a interrupção. Os tempos representam processamento local em CPU, com cache de prefixo, e não capacidade de produção na VPS, latência do canal ou tempo de resolução após encaminhamento humano.

A independência estrita entre desenvolvimento e avaliação não pôde ser certificada retrospectivamente. A auditoria não encontrou payloads completos idênticos entre os splits exportados, mas os identificadores originais de conversa não foram preservados e seis mensagens do golden coincidem exatamente com mensagens de treinamento do experimento anterior. Além disso, a bateria orientou ajustes de regras e a revisão ampliada foi realizada após exposição às saídas. Os dez cenários adicionais disponibilizados nesta revisão são sintéticos e ainda não foram executados no agente; não foram apresentados como pedidos reais ou teste prospectivo independente. A avaliação com novas conversas e gabaritos definidos antes da exposição ao sistema permanece como extensão futura.

## Texto pronto — conclusão equilibrada

Os resultados sustentam a viabilidade técnica da arquitetura e delimitam a participação operacional do componente de linguagem. A maior parte dos casos foi conduzida pelos caminhos determinísticos, e o ramo híbrido ampliou a apresentação de produtos em um subconjunto, com custo adicional de inferência. A conferência profissional e a revisão das referências ampliaram a análise do cenário estudado, sem eliminar lacunas de estado, seguimento da conversa ou qualidade cadastral. Assim, o estudo não reivindica superioridade comercial geral do híbrido nem generalização irrestrita. Suas contribuições são a integração implementada, a comparação controlada dentro do protocolo declarado, a rastreabilidade dos resultados e a identificação reproduzível das limitações e próximos ajustes.

## Como usar os números da revisão recebida

As tabelas abaixo foram recontadas a partir dos três JSONs do ZIP. São classificações por rubrica, não estimativas de precisão comercial obtidas por três pessoas. O autor informou a conferência de dois profissionais, mas não forneceu atribuição individual de cada escore a um profissional ou registros de adjudicação. Por isso, esses números devem permanecer identificados como análise descritiva auxiliar, sem inventar avaliações independentes ou substituir “parcial” por “adequado”.

| Rubrica | Condição | Adequadas | Parciais | Inadequadas | Indeterminadas | Total |
| --- | --- | --- | --- | --- | --- | --- |
| Aplicação | D | 122 | 135 | 29 | 85 | 371 |
| Aplicação | H | 119 | 131 | 34 | 87 | 371 |
| Auditoria | D | 103 | 125 | 143 | 0 | 371 |
| Auditoria | H | 106 | 113 | 152 | 0 | 371 |
| Balcão | D | 103 | 127 | 141 | 0 | 371 |
| Balcão | H | 106 | 115 | 150 | 0 | 371 |

Os resultados variam conforme a dimensão: há três adequações adicionais em H nas rubricas de balcão/auditoria, mas três a menos na de aplicação. Os critérios são distintos e dependentes, portanto não devem ser somados como votos de três especialistas ou usados para afirmar um vencedor comercial geral. Nos sete IDs com produtos adicionais, cinco Top-1 são sustentados cadastralmente e dois permanecem indeterminados na revisão recebida; mesmo um Top-1 sustentado pode coexistir com erro de composição ou candidatos adicionais não aprovados.

## O que registrar e o que manter como limitação

| Pode registrar | Formulação a evitar sem evidência adicional |
| --- | --- |
| Dois profissionais com 10 e 7 anos conferiram os 371 casos, conforme confirmação do autor. | Três especialistas independentes avaliaram todos os casos. |
| H apresentou produtos em sete IDs adicionais, equivalentes a seis pedidos distintos. | A LLM acertou sete novos atendimentos ou provou maior precisão comercial. |
| Três repetições da versão congelada, com saídas estáveis e tempos arquivados. | Três amostras independentes de clientes ou teste sem interrupções/cache. |
| Auditoria de sobreposição, com os limites de metadados e de desenvolvimento explicitados. | Ausência de vazamento ou independência de conversas definitivamente comprovadas. |
| Dez controles sintéticos documentados para execução futura. | Dez pedidos reais novos já executados como teste independente. |
| Comparação D/H do runtime base; comparação LoRA anterior descrita separadamente. | D é o modelo antigo e H é o modelo com fine-tuning. |

O percentual anterior de 19,1% pertence à comparação de fine-tuning de 19/10. Os 12,1% pertencem à nova ablação da arquitetura em 26–27/10. Não substituir um número pelo outro sem identificar o experimento, o backend, o motor de inferência e a fonte. A revisão recebida reexaminou resultados arquivados; ela não executou novamente os 3.408 casos nem testou o adapter no Ollama.

## Integridade e alcance desta conferência

A auditoria deste adendo conferiu o CRC e 39 hashes internos do ZIP recebido, sua correspondência com os 3.716 arquivos do manifesto da entrega original e a chave A/B, além das 18 combinações de conjunto/repetição/configuração. Os totais por rubrica e o conjunto dos sete IDs adicionais foram reproduzidos. Não foram executados os scripts recebidos, novas inferências, consultas ao ERP atual ou testes mecânicos. A auditoria verifica integridade e consistência das contagens; não cria um terceiro parecer comercial independente.

Foi registrada uma ressalva de empacotamento: o manifesto de congelamento original menciona um cache Python derivado, gateway_frozen/ui/__pycache__/streamlit_app.cpython-314.pyc, que foi excluído do pacote. Os outros 198 arquivos desse manifesto estão presentes e conferem nos hashes. O bytecode pode ser regenerado a partir da fonte; sua ausência não equivale à ausência do código-fonte nem altera os resultados arquivados. O ZIP original e os manifestos foram preservados, e a exceção está explicitada em AUDITORIA_DA_REVISAO.json.

## Registro profissional e documentação ainda não informada

| Identificação anônima | Domínio informado | Experiência | Cobertura confirmada pelo autor |
| --- | --- | --- | --- |
| PROF_VENDAS | Vendas de autopeças | 10 anos | 371 casos |
| PROF_APLICACAO | Aplicação de peças | 7 anos | 371 casos |

Esses fatos foram registrados em REGISTRO_DA_REVISAO_PROFISSIONAL.json. Não foram informados a data exata dos pareceres, se cada profissional julgou antes de consultar o outro e quais valores dos três arquivos foram assumidos individualmente. Isso não apaga a conferência profissional declarada; apenas delimita as alegações metodológicas. A redação pronta acima descreve a revisão realizada sem presumir esses procedimentos.

## Resposta curta para a defesa

Os apontamentos foram tratados com uma ablação entre o fluxo determinístico e o híbrido, três repetições de uma versão congelada e revisão dos 371 casos por dois profissionais, com dez e sete anos de experiência. A LLM participou de 12,1% dos casos e ampliou a apresentação de produtos em sete IDs, correspondentes a seis pedidos distintos. Esses dados mostram contribuição operacional localizada, não superioridade comercial geral. O trabalho mantém explícitas as limitações da amostra, da fonte cadastral e da independência retrospectiva; os novos cenários sintéticos não foram apresentados como teste independente já executado.
