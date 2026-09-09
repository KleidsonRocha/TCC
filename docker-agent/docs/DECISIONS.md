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

### Revisao visual agrupada por conversa

Decisao:

- mostrar a conversa completa no Streamlit, mas revisar e persistir o rotulo por interacao
- retirar a conversa da fila pendente somente quando todos os seus turnos tiverem sido revisados ou descartados
- manter `reviewed` separado de `promoted`, sem transformar uma avaliacao humana diretamente em dado de treino
- expor a operacao por uma API administrativa do `docker-agent`, opcionalmente protegida por chave, sem dar acesso direto do Streamlit ao Postgres

Motivo:

- o contexto multi-turno e necessario para julgar follow-ups e contraperguntas
- a granularidade por interacao preserva o formato atual do dataset e a rastreabilidade
- a separacao entre revisao e promocao cria uma segunda barreira de qualidade antes do fine-tuning
- a API concentra validacao, concorrencia e transicoes de estado no servico dono dos dados

Complemento multi-item:

- persistir `predicted_items` e `reviewed_items` sem substituir `criteria`
- revisar cada item com decisao, campos faltantes e pergunta proprios
- manter a estrutura curada em `expected_items` na promocao e exportar os criterios em `items` no contrato supervisionado
- permitir reabertura somente de `reviewed` ou `discarded`, registrando o estado anterior em `pre_search_review_revision`
- bloquear reabertura de exemplos ja promovidos ate a retirada explicita do dataset

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

## 13. Elegibilidade conservadora para perguntas deterministicas

Status:

- contrato definido e testado
- integracao ao runtime concluida

Decisao:

- permitir o `deterministic_ask` somente para uma familia canonica encontrada por alias exato na mensagem atual ou para um pedido explicitamente automotivo sem familia
- calcular `missing_fields`, pergunta e opcoes exclusivamente pelas regras e templates do backend
- escolher sempre o primeiro campo pela prioridade fixa: `part_query`, `vehicle_model`, `vehicle_year`, `engine`, `side`, `position`, `axle`, `variant`
- nao reaproveitar historico antigo para provar a elegibilidade inicial; o historico continua disponivel no fluxo completo da LLM e no tratamento posterior de follow-up
- encaminhar para a LLM qualquer fuzzy isolado, descricao funcional, sintoma, mudanca de assunto, intencao de handoff, candidato de peca nao resolvido ou estado com pergunta pendente
- manter `part_code` fora desse bypass especifico, preservando o caminho que ja valida sua proveniencia

Motivo:

- uma pergunta deterministica so e segura quando o backend conhece tanto o campo ausente quanto a redacao permitida para solicita-lo
- restringir a evidencia a mensagem atual evita que uma familia antiga seja tratada como o assunto atual
- fuzzy e recuperacao semantica expressam aproximacao, nao confirmacao, e por isso nao podem consolidar familia automaticamente

Consequencia:

- o use case tenta `deterministic_bypass` para `search`, depois `deterministic_ask` e somente entao a LLM
- a ativacao possui a feature flag independente `PRE_SEARCH_DETERMINISTIC_ASK_ENABLED`, fallback imediato para LLM e telemetria `pre_search_path = deterministic_ask`
- pergunta, opcoes, criterios e campos ausentes reutilizam o contrato do backend e produzem o mesmo `ConversationState` persistido pelo `docker-comm` no Redis
- a LLM permanece responsavel por todos os casos que nao satisfazem integralmente a politica conservadora

## 14. `no_match` como resultado de consulta, nao prova de incompatibilidade

Decisao:

- tratar zero linhas como ausencia de itens correspondentes aos filtros enviados ao ERP
- listar os criterios pesquisados e separar esse caso de criterio ainda insuficiente ou divergente do contexto anterior
- preservar criterios conhecidos do `ConversationState` somente em continuacoes pendentes da mesma familia
- nunca restaurar `part_code` a partir do estado e nunca reaproveitar criterios quando a familia atual mudou
- manter `handoff.required = false` enquanto o atendimento humano estiver apenas sendo oferecido
- persistir `pending_slot = no_match_retry` para permitir correcao e nova tentativa no mesmo Redis conversacional

Motivo:

- uma consulta sem linhas nao demonstra que a peca seja incompativel com o veiculo; pode haver catalogo incompleto, filtro restritivo, divergencia de cadastro ou item indisponivel na camada pesquisada
- pedir novamente modelo, ano e motor ja informados quebra a coerencia multi-turno e ignora o estado que o `docker-comm` ja conserva
- sinalizar handoff antes da escolha do usuario contradiz a mensagem que apenas oferece essa opcao

Consequencia:

- a resposta permite ao usuario auditar os filtros usados e corrigir somente o dado necessario
- follow-ups de nova tentativa continuam pelo fluxo contextual sem criar store ou chave paralela
- o ERP continua sendo a fonte do resultado comercial, mas o backend limita a interpretacao que pode ser comunicada ao usuario

## 15. Desambiguacao de resultados como estado deterministico multi-turno

Decisao:

- estender `PartItem` com atributos opcionais de desambiguacao provenientes da view existente do ERP
- escolher no backend o atributo que realmente divide os candidatos entre aplicacao, versao, motor, lado, posicao, injecao, transmissao e caracteristicas lexicais controladas como `com/sem ar condicionado`
- armazenar candidatos, opcoes, atributo perguntado, campos ja usados e contador de tentativas em `ConversationState.result_disambiguation`
- persistir esse objeto na mesma chave `conv:{conversation_id}:state` usada pelo `docker-comm`, sem novo banco, chave ou store
- aceitar resposta por numero, valor do atributo, codigo ou titulo exato
- usar paginas de ate quatro itens quando nenhum atributo confiavel separar os candidatos
- tratar negacao, mudanca de familia, pedido de handoff e limite de tres tentativas sem consultar a LLM

Motivo:

- devolver dez itens transfere a decisao ao usuario sem conduzir a conversa
- a view do ERP ja possui aplicacao, complemento, motor, injecao e transmissao; esses dados sao evidencia melhor que uma pergunta inventada pela LLM
- manter os candidatos no estado existente permite resolver a proxima mensagem sem repetir a busca nem criar persistencia paralela

Limites:

- um atributo so vira pergunta quando produz pelo menos duas assinaturas distintas e entre duas e seis opcoes curtas
- valores extensos ou que nao separam os itens sao ignorados
- a selecao nao afirma compatibilidade; a resposta ainda solicita confirmacao do codigo antes de finalizar
- mudanca de familia limpa a desambiguacao anterior e reinicia o fluxo normal

Consequencia:

- buscas com varios itens retornam `request_info`, nao uma lista extensa imediata
- a resposta seguinte usa `pre_search_path = result_disambiguation` e nao chama LLM nem ERP
- `result_disambiguation_requested` identifica handoff escolhido pelo usuario e `result_disambiguation_limit` identifica o limite operacional

## 16. Bateria real separa contrato estrutural de aprovacao comercial

Decisao:

- versionar a bateria real em um schema proprio de cenarios e turnos, preservando os 50 casos legados
- usar niveis cumulativos `smoke`, `regression` e `extended`
- automatizar apenas propriedades objetivas, como status, caminho, ferramentas, estado, proveniencia e tipo de acao
- marcar ranking, discriminadores dependentes do ERP e politicas sem resposta unica com `review_required`
- manter uma lista humana separada para promover expectativas comerciais depois da validacao no Streamlit
- gravar execucoes exploratorias em `.tmp/eval/` com nome unico por padrao

Motivo:

- uma assercao ampla pode esconder uma regressao ou falhar por uma mudanca comercial legitima do ERP
- respostas geradas ou inferidas nao devem virar verdade de negocio sem curadoria
- separar os niveis permite feedback rapido sem impedir uma regressao mais ampla antes de releases

Consequencia:

- a bateria passa a ter cobertura multi-turno reproduzivel para `docker-agent` e `docker-comm`
- os relatorios historicos deixam de ser sobrescritos acidentalmente por uma execucao comum
- a lista de validacao mostra exatamente quais casos ainda dependem do responsavel pelo negocio

## 17. Historico anterior e precedencia da mensagem atual

Decisao:

- o runner deve enviar somente mensagens anteriores ao turno avaliado
- uma entidade explicitamente presente na mensagem atual prevalece sobre o estado anterior e sobre a resposta da LLM
- `side`, `position` e `axle` permanecem campos independentes; `eixo dianteiro/traseiro` nao preenche `position`

Motivo:

- respostas futuras no contexto contaminam a validade metodologica da bateria
- troca de veiculo, nova peca e correcoes do usuario sao informacoes novas, nao complementos obrigatorios do estado antigo
- misturar posicao e eixo produz perguntas comerciais incoerentes e filtros incorretos

Consequencia:

- contextos capturados pelo runner sao truncados antes da mensagem atual
- o backend preserva informacoes espontaneas e usa a mensagem atual como autoridade para entidades extraidas
- regressao automatizada cobre vazamento temporal, troca de identidade e separacao eixo/posicao

## 18. Estado multi-item e quantidade conservadora

Decisao:

- adicionar `ConversationState.items` opcional, mantendo `criteria` como item ativo retrocompativel
- criar itens somente para familias reconhecidas em clausulas independentes
- aceitar quantidade apenas com marcador linguistico como `unidades`, `pecas`, `itens`, `x` ou `quantidade`
- preservar frases compostas conhecidas antes da normalizacao de familia

Motivo:

- pedidos reais podem conter varias pecas e criterios diferentes na mesma mensagem
- numeros de ano, modelo, motor e cilindrada nao sao evidencias de quantidade
- reduzir uma composicao a seu substantivo mais conhecido muda o produto procurado

Limite atual:

- a colecao ja e persistida e transportada, mas a pesquisa comercial agregada por item permanece como proxima etapa

## 19. Marca comercial da peca como preferencia

Decisao:

- representar NGK, Nakata, Cofap e marcas equivalentes em `preferred_product_brand`
- manter `vehicle_brand` exclusivamente para a montadora do veiculo
- usar a marca comercial somente como preferencia de ranking no ERP
- continuar retornando itens compativeis de outras marcas quando a preferida nao estiver disponivel

Motivo:

- pedidos reais frequentemente citam uma marca desejada sem exigir exclusividade
- tratar a marca da peca como montadora contamina o criterio do veiculo
- transformar preferencia em filtro rigido pode produzir `no_match` falso e esconder similares validos

Consequencia:

- a LLM, o extractor, o estado conversacional e o dataset preservam a preferencia explicitamente
- o ranking favorece a marca solicitada sem adiciona-la aos filtros obrigatorios da consulta
