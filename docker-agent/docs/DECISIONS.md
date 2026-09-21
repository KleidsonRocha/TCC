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
- apresentar diretamente ate dez resultados, pois alternativas comercialmente validas
  nao exigem a escolha artificial de um unico codigo
- consultar uma janela de ate 50 candidatos e usar paginas de dez itens quando houver
  excedente e nenhum atributo confiavel separar os resultados
- tratar negacao, mudanca de familia, correcao de filtro, pedido de handoff e limite de tres tentativas sem consultar a LLM

Motivo:

- uma pergunta adicional so ajuda quando a resposta elimina candidatos de forma comprovavel
- a view do ERP ja possui aplicacao, complemento, motor, injecao e transmissao; esses dados sao evidencia melhor que uma pergunta inventada pela LLM
- manter os candidatos no estado existente permite resolver a proxima mensagem sem repetir a busca nem criar persistencia paralela

Limites:

- um atributo so vira pergunta quando produz pelo menos duas assinaturas distintas e entre duas e seis opcoes curtas
- valores extensos ou que nao separam os itens sao ignorados
- a selecao nao afirma compatibilidade; a resposta ainda solicita confirmacao do codigo antes de finalizar
- mudanca de familia limpa a desambiguacao anterior e reinicia o fluxo normal
- correcao de um filtro usado na busca tambem limpa candidatos e resultados
  pendentes; somente a familia pode ser recuperada como contexto quando ela
  foi omitida na frase de correcao

Consequencia:

- buscas com ate dez itens retornam a lista diretamente; buscas maiores perguntam
  somente quando houver discriminador confiavel e, nos demais casos, exibem a
  primeira pagina com a opcao `ver mais`
- a resposta seguinte usa `pre_search_path = result_disambiguation` e nao chama LLM nem ERP
- `result_disambiguation_requested` identifica handoff escolhido pelo usuario e `result_disambiguation_limit` identifica o limite operacional

### Indicadores publicos da busca

- `confidence` representa a confianca heuristica do fluxo na decisao tomada; nao e
  probabilidade comprovada de encaixe da peca
- `score` ordena a relevancia dos candidatos retornados; nao confirma aplicacao,
  disponibilidade ou compatibilidade comercial
- qualquer calibracao numerica desses indicadores depende de exemplos rotulados por
  avaliador humano e das metricas top-1, top-3, incompatibilidade, empate e `no_match`

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

## 20. Identidade De Familia E Aplicacao Veicular No Contrato ERP V2

Decisao:

- identificar a familia pelo subgrupo canonico do item, antes de qualquer ranking
- preservar uma linha por `produto_veiculos.id_geral` no novo objeto `soccol.item_search_applications`
- exigir marca, modelo, ano, motor e versao na mesma aplicacao; modelo usa igualdade normalizada
- obter motores, injecoes e transmissoes pelas relacoes `produto_veiculos_*`, nunca pelas possibilidades gerais do modelo
- manter intervalos independentes e reconhecer fim aberto somente pela marcacao explicita da aplicacao
- fornecer atributos de desambiguacao apenas das aplicacoes que passaram pelos filtros
- exportar ERP e snapshot pelo mesmo SELECT, em transacao consistente e UTF-8, com verificacao de checksum

Motivo:

- agregados por item cruzavam atributos de veiculos e periodos diferentes; `MIN/MAX` preenchia lacunas inexistentes
- substring aceitava `Golf` ao procurar `Gol`, e texto de acessorio podia superar a peca pedida no ranking
- o ERP usa WIN1252; copiar bytes sem conversao impedia carregar o snapshot no PostgreSQL UTF-8 local

Consequencias:

- o contrato v2 exige migracao coordenada de SQL externo, runtime e fallback
- o snapshot v1 permanece legado; suas colunas agregadas nao permitem reconstruir proveniencia com seguranca
- falta de motor ou ano comprovado pode reduzir resultados; texto livre nao e usado para inventar compatibilidade
- o golden set ERP valida contrato e COPY, incluindo os quatro candidatos controlados da auditoria; `--integration-sql` adiciona auditoria dos SELECTs de origem fornecidos localmente

## Organizacao De Artefatos Em 14/09/2026

- schema e carga do banco local ficam em `db/init/pre_search_init.sql`; o instalador reutiliza somente seu bloco de fallback
- snapshots gzip ficam no Git LFS; manifestos e checksums ficam no Git comum com finais de linha LF
- DDL do ERP pertence a operacao do banco quente e fica fora do Git; o contrato e a proveniencia exigida permanecem documentados
- exportacao le as views instaladas em `REPEATABLE READ, READ ONLY`, em UTF-8 e com ordem explicita de colunas, sem depender do arquivo DDL
- historico de relatorios e backlog legado fica em `HISTORICO.md`; saidas de execucao ficam em `.tmp/eval/`

## 21. Negacao E Conflito De Veiculo Sao Resolvidos Antes Da Busca

Decisao:

- resolver substituicao explicita como `nao quero X, quero Y` para somente Y;
- excluir direcoes negadas da extracao, preservando a direcao afirmativa;
- nao criar `items[]` a partir de uma clausula negativa;
- responder com `intent_resolution` quando a negacao ou correcao nao possui
  alvo afirmativo seguro;
- responder com `vehicle_identity` quando a marca conflita com a relacao
  modelo/montadora comprovada no catalogo; `vehicle_model_brand.csv` alimenta
  essa relacao durante o bootstrap.

Motivo:

- uma busca pode ser estruturalmente completa e ainda contrariar o pedido do
  cliente se uma negativa for lida como item ou filtro positivo;
- marca e modelo contraditorios nao comprovam uma aplicacao veicular.

Consequencia:

- os caminhos `deterministic_bypass`, `deterministic_ask` e LLM passam pelo
  mesmo gate de seguranca antes de chamar o ERP;
- a pergunta resultante fica no `ConversationState`, para que a proxima
  mensagem complete a intencao em vez de manter uma combinacao insegura.

## 22. Contexto Veicular E Identidade De Item Sao Locais A Clausula

Decisao:

- deduplicar itens pela combinacao completa de criterios, e nao somente por
  familia, lado e posicao;
- manter marca, modelo, ano e motor encontrados na propria clausula;
- compartilhar a aplicacao somente quando o veiculo estiver explicitamente
  associado ao conjunto no fim do pedido, como `radiador e pastilha para Gol`.

Motivo:

- dois pedidos da mesma familia podem ser para veiculos e motores distintos;
- herdar o veiculo da frase inteira transforma uma ausencia de dado em filtro
  inventado e pode retornar uma peca incompatível.

Consequencia:

- `ConversationState.items` preserva cada aplicacao para o gate e a pesquisa
  individual posteriores;
- a validacao executavel foi adicionada, mas golden set e bateria ficaram
  pendentes de execucao a pedido do usuario.

## 23. Curadoria Prioriza Novidade Sobre Volume

- revisar conversas por `conversation_id` e comparar candidatas com exemplos
  ja promovidos;
- descartar duplicatas, contexto contaminado e selecao sem aplicacao provada;
- promover somente cobertura nova de familia, estado ou seguranca;
- manter casos bloqueados como `reviewed` ate a evidencia de catalogo existir.

## 24. Falha De Busca E Ausencia De Produto Sao Estados Distintos

Decisao:

- devolver HTTP 503 quando a unica busca ERP nao puder ser executada;
- em pedidos com varias pecas, manter o resultado de cada item, incluindo
  `error`, para que o cliente possa repetir apenas a parte indisponivel;
- registrar os estados por item na captura de revisao e na telemetria.

Motivo:

- `no_match` afirma que a consulta foi concluida sem resultado; usa-lo para uma
  falha de infraestrutura induz o atendimento e a curadoria ao diagnostico
  errado.

## 25. I/O Sincrono Roda Em Workers Limitados

Decisao:

- manter as integracoes existentes sincrona em workers via `asyncio.to_thread`;
- limitar inferencia e busca por configuracao e aplicar prazo externo ao worker;
- aplicar tambem `statement_timeout` no PostgreSQL;
- manter a auditoria da LLM em `ContextVar` por requisicao.

Motivo:

- a migracao completa de todos os clientes para APIs assincronas aumentaria o
  escopo sem melhorar o contrato. O isolamento atual preserva as integracoes e
  impede que uma chamada lenta bloqueie o loop da FastAPI.

## 26. Motor Textual E Uma Opcao Governada Pelo Catalogo

Decisao:

- carregar de `pre_search_engine_option` o nome da motorizacao e seus anos de
  vigencia, alem da lista usada para sugerir respostas;
- em resposta a uma pergunta pendente de motor, canonizar somente uma opcao
  textual inteira do modelo ativo, priorizando a forma mais especifica;
- aceitar a resposta quando algum intervalo conhecido cobre o ano informado;
  se nao houver intervalo, manter a evidencia para a camada posterior, sem
  inventar compatibilidade;
- interpretar tokens como `BE`, `Zetec Rocam`, `Duratec HE`, `Sigma`, `EA111`
  e `EA211` como motor nesse contexto, e nao como codigo de peca.

Motivo:

- o catalogo ja possui esses nomes e intervalos, mas o runtime carregava apenas
  a lista visual e extraia somente cilindrada numerica;
- repetir a mesma pergunta depois de uma resposta catalogada perde evidencia e
  degrada o atendimento.

Consequencia:

- o follow-up preenche o item pendente e avanca para o proximo atributo
  obrigatorio; `coxim amortecedor` ainda pergunta a posicao quando ela faltar;
- uma motorizacao incompatavel com o ano conhecido nao libera busca
  deterministica.

## 27. Lista Comercial E Delimitada Por Aliases Do Catalogo

Decisao:

- localizar todas as ocorrencias exatas e nao sobrepostas de aliases de familia
  em uma mensagem antes de depender de virgulas ou da conjuncao `e`;
- construir cada `SearchCriteria` com o texto entre sua ancora e a proxima,
  preservando quantidade, lado, posicao e aplicacao locais;
- compartilhar uma aplicacao apenas quando ela estiver antes da primeira ou
  depois da ultima peca e o item nao tiver marca ou modelo proprio;
- manter itens sem veiculo como pendentes parciais, em vez de completar seus
  campos com outra clausula da lista.

Motivo:

- pedidos reais enumeram produtos por espacos, abreviacoes e quantidades;
  separar somente por pontuacao colapsava a lista em uma familia;
- copiar ano ou motor de uma peca para outra transforma ausencia de evidencia
  em um filtro falso no ERP.

Consequencia:

- os casos `real_005`, `real_052`, `real_055`, `real_067` e `real_081` cobrem
  listas comerciais, veiculos distintos e sucesso parcial sem frases especiais
  no runtime;
- novos sinonimos continuam sendo adicionados ao catalogo, nao a uma lista de
  excecoes do extractor.

## 28. Prompt Da LLM Residual E Um Contrato De Evidencia

Decisao:

- chamar a LLM somente depois de os caminhos deterministicos nao produzirem
  busca ou pergunta governada;
- enviar o payload residual com fontes separadas e ordem explicita: mensagem
  atual, seed extraido dela, estado do item ativo para campos omitidos,
  mensagens anteriores do usuario para omissoes e mensagens do assistant como
  contexto nao factual;
- instruir a LLM a nao reutilizar historico que conflite com a mensagem atual;
- manter o backend como autoridade para canonizacao, proveniencia de codigo,
  campos obrigatorios, score e decisao de busca.

Motivo:

- um historico misturado sem origem torna facil confundir uma pergunta ou uma
  resposta anterior do assistente com fato informado pelo cliente;
- a LLM deve conduzir casos residuais, nao substituir o contrato operacional.

Consequencia:

- o payload e auditavel por fonte de evidencia;
- uma saida da LLM continua sendo candidata e passa pelos mesmos gates do
  backend antes de chegar ao ERP.

## 29. Direcoes Publicas Usam Vocabulario Unico

Decisao:

- publicar `side` como esquerdo/direito, `position` como dianteiro/traseiro e
  `axle` como eixo dianteiro/traseiro;
- gerar perguntas desses tres campos pelo backend, mesmo quando a LLM sugerir
  outra redacao;
- normalizar equivalentes de genero e ingles na desambiguacao, preservando
  `position` e `axle` como atributos diferentes.

Motivo:

- textos como `lateral`, `frente` e `eixo` sem padrao confundem a resposta do
  cliente e dificultam retomar o estado;
- eixo nao e sinonimo de posicao: cada um filtra uma caracteristica distinta.

Consequencia:

- regras de familia continuam decidindo quando perguntar eixo;
- a desambiguacao pode usar eixo quando os candidatos realmente o separam,
  exibindo uma opcao compreensivel e consistente.

## 30. ERP Quente E A Fonte Operacional; Snapshot E Contingencia

Decisao:

- usar o ERP quente pelo backend `erp_postgres` como fonte operacional da
  busca e manter o snapshot local v2 para contingencia e reproducao;
- distinguir indisponibilidade de ausencia de produto e executar I/O de
  inferencia, PostgreSQL e revisao fora do event loop, com limite, timeout e
  auditoria por requisicao.

Motivo:

- o snapshot permite recuperar e repetir testes, mas nao prova disponibilidade
  comercial atual; falha tecnica nao pode virar `no_match`;
- isolamento evita bloquear saude e misturar auditorias de conversas distintas.

Consequencia:

- beta e avaliacao de ranking devem medir o ERP quente com rotulos humanos;
- o snapshot permanece verificavel sem mascarar falha da fonte operacional.
