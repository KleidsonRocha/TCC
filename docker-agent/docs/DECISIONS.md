# Registro De Decisoes Tecnicas

Este documento concentra os motivos das escolhas principais do projeto. O objetivo e evitar que a justificativa fique espalhada entre backlog, relatorios e historico de execucao.

## 1. Catalogo deterministico no Postgres como fonte de verdade

Decisao:

- usar o Postgres como fonte unica para regras de negocio, aliases, familias de peca e parametros de decisao

Motivo:

- permite governanca explicita das regras
- facilita auditoria e reproducao
- evita espalhar conhecimento de dominio em codigo hardcoded

Consequencia:

- o runtime depende do banco corretamente bootstrapado
- mudancas estruturais exigem refletir `db/init/pre_search_init.sql` e os CSVs reais em `db/init/csv/`

## 2. Bootstrap real versionado no repositorio

Decisao:

- manter os CSVs reais de bootstrap em `db/init/csv/`
- remover templates duplicados de `docs/assets/`

Motivo:

- reduz ambiguidade entre exemplo e dado operacional
- simplifica a reproducao do ambiente em outra maquina
- evita divergencia entre documentacao e bootstrap real

## 3. LLM como validador e orquestrador, nao como decisor isolado

Decisao:

- executar extracao deterministica antes da LLM
- enviar `dictionary_seed_criteria` e `score_policy` para a LLM
- recalcular o gate de `search` no backend apos a resposta da LLM

Motivo:

- reduz risco de alucinacao
- preserva rastreabilidade das regras de negocio
- melhora consistencia em casos com campos obrigatorios como `engine`, `side` e `position`

## 4. Gate backend para liberar `search`

Decisao:

- a LLM pode sugerir `search`, mas a decisao final depende do backend validar score e campos obrigatorios

Motivo:

- evita liberar busca cedo demais
- protege o sistema de respostas otimistas ou inconsistentes da LLM
- separa claramente regra deterministica de comportamento linguistico

## 5. Captura, revisao e promocao antes do fine-tuning

Decisao:

- manter `pre_search_review_interaction` como fila bruta de interacoes reais
- promover apenas casos revisados para `pre_search_fine_tuning_dataset_record`

Motivo:

- impede que ruido operacional vire treino automaticamente
- preserva qualidade metodologica do dataset
- separa evento real de verdade supervisionada curada

## 6. Fine-tuning com SFT + LoRA/QLoRA

Decisao:

- usar `supervised fine-tuning` sobre o modelo base
- aplicar `LoRA`
- preferir `QLoRA` quando houver GPU compativel

Motivo:

- o projeto possui dataset supervisionado estruturado, nao dataset de preferencias
- `QLoRA` reduz custo computacional e memoria
- viabiliza experimentos em GPU unica, sem exigir full fine-tuning do backbone inteiro

Alternativas nao escolhidas como abordagem principal:

- full fine-tuning: custo desproporcional para o escopo do projeto
- RLHF/DPO: menos aderentes ao tipo de dado disponivel
- ajuste somente por prompt: insuficiente como estrategia unica para especializacao persistente

## 7. Runtime e trainer separados

Decisao:

- manter o ambiente de treino em container proprio (`trainer`)
- nao acoplar dependencias pesadas de treino ao `docker-agent`

Motivo:

- reduz complexidade do runtime operacional
- separa inferencia de experimentacao
- facilita reproduzir o ambiente de API sem precisar carregar stack de GPU

## 8. Publicacao do resultado como adapter sobre o modelo base

Decisao:

- gerar `adapter` e empacotar no Ollama como novo modelo

Motivo:

- preserva o modelo base original
- facilita comparacao entre baseline e candidato
- simplifica rollback

## 9. Melhorias estruturais antes de ampliar a camada de ML

Decisao:

- priorizar correcoes de catalogo, canonizacao, gates e regressao automatizada antes de introduzir novos modelos auxiliares

Motivo:

- evita usar ML para mascarar falhas de regra ou dado
- melhora a qualidade do dataset que depois sera usado no fine-tuning
- mantem o escopo do TCC tecnicamente defensavel

## 10. Classificador auxiliar em portugues como hipotese futura, nao prioridade atual

Decisao:

- nao introduzir agora um modelo auxiliar como `BERTimbau` para slot filling

Motivo:

- o ganho potencial ainda nao compensa o custo adicional de arquitetura, dados e testes
- a prioridade atual continua sendo estabilizar as regras deterministicas e o fluxo principal

## 11. Recuperacao semantica por embeddings como evolucao candidata para pedidos genericos

Status:

- opcao levantada e considerada promissora para avaliacao futura
- implementacao condicionada ao fechamento das prioridades estruturais e a ganho comprovado em benchmark

Decisao:

- avaliar uma camada de recuperacao semantica sobre as familias reais de `pre_search_part_type`
- acionar essa camada somente quando alias exato e fuzzy nao identificarem `part_query` com seguranca
- usar os scores apenas para selecionar candidatos e apoiar uma pergunta de confirmacao
- gerar no backend uma pergunta curta por template usando somente candidatos controlados, aguardar a resposta do usuario e somente entao consolidar a familia canonica
- usar a LLM para redacao semantica apenas se um benchmark futuro demonstrar ganho de qualidade que justifique a latencia
- reutilizar o historico e o `ConversationState` que o `docker-comm` ja persiste no Redis
- manter a primeira fase restrita a familias do catalogo, sem vetorizar todos os itens do ERP

Motivo:

- pedidos genericos como `aquilo que segura o carro` expressam funcao ou sintoma e nao sao bem resolvidos apenas por igualdade lexical ou distancia de edicao
- embeddings podem aproximar esse texto de familias como suspensao, amortecedor ou mola e oferecer opcoes reais do catalogo
- a confirmacao pelo usuario reduz o risco de transformar proximidade semantica em identificacao incorreta
- o encaixe preserva a arquitetura atual: banco como fonte estrutural, backend como autoridade, LLM como fallback contextual e Redis como estado multi-turno

Limites da decisao:

- similaridade vetorial nao valida compatibilidade veicular
- embedding nao libera `search` sozinho
- a pergunta de confirmacao nao depende obrigatoriamente da LLM
- alias exato, fuzzy matching, regras de catalogo, gate backend e filtros do ERP continuam prioritarios
- falha ou timeout da recuperacao semantica deve seguir pelo fluxo atual
- a adocao definitiva depende de medir acerto `top-1`, cobertura `top-3`, falsos positivos, confirmacao do usuario e latencia

Consequencia:

- o backlog passa a prever dataset semantico curado, prova de conceito, extensao opcional do `ConversationState`, testes multi-turno e rollout por feature flag
- se a prova de conceito nao superar o baseline atual, a camada nao deve ser promovida para o runtime

## 12. Bypass deterministico antes da LLM para casos comprovadamente completos

Decisao:

- liberar diretamente `search` quando extractor, catalogo, regras obrigatorias e score forem suficientes
- aceitar no bypass somente alias exato, `part_code` literal validado ou follow-up simples que preencha o `pending_slot`
- manter todos os casos incertos no caminho de validacao por LLM
- preservar a persistencia conversacional existente no Redis por meio do mesmo `ConversationState`
- permitir rollback por `PRE_SEARCH_DETERMINISTIC_BYPASS_ENABLED=false`

Motivo:

- a bateria real mostrou que a inferencia da LLM era o maior custo nos fluxos mais comuns
- pedidos ja resolvidos pelas regras nao ganham qualidade ao repetir a mesma decisao na LLM
- a medicao real reduziu a latencia de `71668.38 ms` para `1313.73 ms` no pedido completo e de `46730.79 ms` para `926.96 ms` no follow-up

Limites:

- fuzzy sozinho nao libera o bypass
- familia generica, requisito faltante, motor textual ou estado incerto exigem LLM
- o bypass so produz `search`; perguntas e handoffs continuam no fluxo completo
- o gate backend, a proveniencia de `part_code` e a busca/ranking do ERP permanecem autoridades independentes

Consequencia:

- `tool_trace` passa a expor `pre_search_path` e latencia de pre-busca, ERP e montagem de resposta
- GPU continua relevante apenas para reduzir o custo residual dos casos que realmente precisam de inferencia
- `LLM_KEEP_ALIVE` e prompt so devem mudar depois de comparacao mensuravel posterior ao bypass
