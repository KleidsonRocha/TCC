# TODO - Backlog Priorizado Do Produto (docker-agent)

Este arquivo contem somente trabalho ainda pendente. Entregas concluidas, evidencias e decisoes historicas ficam em `PROGRESS.md` e `DECISIONS.md`.

## Ordem Atual

1. reduzir novas chamadas obvias a LLM sem perder seguranca
2. corrigir coerencia multi-turno e respostas finais
3. melhorar a qualidade da busca e da apresentacao dos itens do ERP
4. tratar descricoes funcionais e sintomas com recuperacao semantica controlada
5. otimizar a infraestrutura apenas para os casos que ainda precisarem de LLM
6. executar o ciclo de fine-tuning na janela operacional com GPU

Regra para buscas genericas ou incertas:

- falta obvia de um criterio conhecido: responder com `ask` deterministico
- descricao funcional, sintoma ou expressao popular: avaliar recuperacao semantica com confirmacao
- ambiguidade contextual real ou caso fora das regras: manter a LLM
- GPU, modelo menor e tuning de inferencia entram somente para o volume residual de LLM

## Criterio Obrigatorio Para Cada Bloco

Toda prioridade implementada deve:

- transformar casos reais afetados em regressao automatizada
- executar testes focados e a suite completa
- medir `pre_search_path` e `stage_latency_ms` quando tocar runtime
- reexecutar os casos correspondentes da bateria real
- comparar qualidade e latencia antes/depois
- atualizar `PROGRESS.md`, `DECISIONS.md` e o fluxo runtime quando houver mudanca arquitetural
- evitar relatorio duplicado quando um artefato consolidado puder ser atualizado

## Prioridade 0 - Criar `ask` deterministico para incompletude obvia

Objetivo:

- evitar uma chamada de dezenas de segundos a LLM quando extractor, catalogo e regras ja sabem exatamente qual informacao falta
- complementar o bypass de `search` existente sem relaxar o gate de seguranca

- [ ] Definir criterios conservadores do bypass de `ask`
  - liberar somente quando a pergunta seguinte puder ser determinada pelas regras do backend
  - cobrir familia exata com campo obrigatorio ausente, como `radiador gol 2010 -> engine`
  - cobrir pedido explicitamente automotivo sem familia, como `quero uma peca -> part_query`
  - usar prioridade deterministica quando mais de um campo estiver ausente
  - nao aplicar a descricao funcional, sintoma, mudanca de assunto ou intencao de handoff
  - nao transformar fuzzy inseguro em familia confirmada

- [ ] Implementar o caminho `deterministic_ask`
  - reutilizar catalogo, `missing_fields`, `NextQuestion` e opcoes ja governadas pelo backend
  - manter o mesmo `ConversationState` enviado ao `docker-comm` e persistido no Redis
  - preservar proveniencia de `part_code`, canonizacao e regras especificas da familia
  - manter fallback imediato para a LLM quando qualquer criterio de elegibilidade falhar
  - disponibilizar feature flag independente para rollback

- [ ] Medir cobertura e ganho do novo caminho
  - distinguir o `deterministic_bypass` atual de `deterministic_ask` e `llm` na telemetria
  - medir quantas perguntas obvias deixam de chamar a LLM
  - comparar latencia de pedidos incompletos e follow-ups antes/depois
  - garantir que a taxa de perguntas incorretas nao aumente

- [ ] Criar regressoes minimas
  - `radiador gol 2010 -> perguntar engine`
  - `bandeja ecosport 2008 -> perguntar side`
  - `quero uma peca -> perguntar part_query`
  - typo inseguro -> continuar na LLM
  - descricao por sintoma -> nao usar `ask` deterministico de familia
  - pedido fora do dominio -> continuar elegivel a handoff pela LLM

## Prioridade 1 - Fazer a conversa ficar coerente ate o fim

- [ ] Corrigir follow-up com motor textual
  - reconhecer `zetec rocam`, `duratec`, `duratec he`, `sigma`, `ea111`, `ea211` e equivalentes catalogados como `engine`
  - validar o valor contra as opcoes do modelo quando houver lista conhecida
  - permitir que um motor textual complete o `pending_slot` e seja elegivel ao caminho deterministico quando seguro
  - revalidar `coxim amortecedor ecosport 2008 -> zetec rocam`

- [ ] Melhorar a resposta de `no_match`
  - separar ausencia real no ERP de criterio ainda insuficiente ou conflitante
  - usar `conversation_state` para nao pedir novamente modelo, ano ou motor ja informados
  - informar quais criterios foram pesquisados
  - oferecer nova tentativa ou handoff sem afirmar incompatibilidade que o ERP nao comprovou

- [ ] Criar desambiguacao real quando houver muitos itens
  - escolher o melhor discriminador seguinte entre aplicacao, versao, motor, lado, posicao e outros dados disponiveis
  - perguntar em vez de apenas devolver uma lista extensa
  - tratar `result_disambiguation` como etapa funcional multi-turno
  - resolver selecao, negacao, mudanca de assunto e limite de tentativas
  - reutilizar o Redis atual, sem store paralelo

- [ ] Reestruturar o prompt residual da LLM como contrato operacional
  - aplicar somente aos casos que nao foram resolvidos deterministicamente
  - definir precedencia entre mensagem atual, mensagens `user`, `ConversationState`, seed e historico
  - tratar mensagens `assistant` apenas como contexto, nunca como fonte factual de slot
  - incluir exemplos minimos de `ask`, `search` e `handoff`
  - manter backend como autoridade final para score, campos obrigatorios, canonizacao e `part_code`

- [ ] Padronizar perguntas e respostas publicas
  - `side` significa esquerdo/direito
  - `position` significa dianteiro/traseiro
  - `axle` so aparece quando fizer sentido para a familia
  - manter perguntas curtas, especificas e coerentes com o campo pendente

## Prioridade 2 - Melhorar a qualidade da busca no ERP

- [ ] Refinar ranking do ERP
  - penalizar itens correlatos quando o usuario pediu a peca principal
  - reduzir ruido de `tampa`, `mangueira`, `kit`, `parafuso`, `lampada` e similares
  - reduzir empates de score
  - priorizar aplicacao exata sobre familia apenas relacionada
  - definir pesos de complemento, injecao, motor e transmissao expostos por `soccol.item_search_candidates`

- [ ] Corrigir apresentacao de texto e encoding
  - manter normalizacao interna sem acento separada do texto exibido ao usuario
  - garantir UTF-8 valido nos titulos e mensagens publicas
  - eliminar mojibake e revisar o uso intencional de textos sem acentuacao
  - nao alterar a identidade ou o ranking do item apenas para corrigir apresentacao

- [ ] Expandir pre-validacao lexical com seguranca
  - melhorar typos e abreviacoes de `part_query` e `vehicle_model`
  - manter alias exato prioritario e fuzzy incapaz de liberar `search` sozinho
  - medir falso positivo e margem para o segundo candidato
  - promover expressoes recorrentes confirmadas para alias curado quando isso for mais simples que ML

- [ ] Reexecutar bateria real focada em ranking
  - comparar item principal contra correlatos
  - registrar `top-1`, qualidade do `top-3`, empates e `no_match`
  - revisar os pesos somente com evidencia do ERP real

## Prioridade 3 - Recuperacao semantica para descricoes genericas

Objetivo:

- tratar funcao, sintoma e expressao popular quando alias e fuzzy nao identificarem a familia
- recuperar somente familias reais de `pre_search_part_type`
- confirmar com o usuario antes de consolidar `part_query`
- reduzir, quando seguro, a necessidade de LLM tambem nesse fluxo

### 3.1 Baseline e prova de conceito

- [ ] Montar dataset semantico separado do fine-tuning
  - incluir pedidos explicitos, typos, descricoes funcionais, sintomas, ambiguidades e mensagens fora do dominio
  - incluir confirmacao pelo nome, numero da opcao, negacao e `nenhuma dessas`
  - registrar familia esperada e alternativas aceitaveis

- [ ] Registrar baseline atual
  - medir extractor isolado e extractor + LLM
  - medir acerto `top-1`, cobertura `top-3`, falso positivo, handoff e latencia
  - definir ganho minimo para promover a hipotese

- [ ] Criar documentos semanticos curados por familia
  - vincular cada documento ao `part_type_id`, grupo e subgrupo
  - separar `description`, `customer_phrase`, `symptom` e `usage`
  - incluir exemplos negativos para familias facilmente confundidas
  - versionar o conteudo humano em CSV real de `db/init/csv/`
  - nao armazenar vetores manualmente no CSV

### 3.2 Modelo e recuperador

- [ ] Comparar modelos de embedding adequados para portugues
  - registrar nome, versao, dimensao, licenca, tamanho e latencia
  - avaliar expressoes reais de autopecas
  - usar a mesma versao para documentos e consultas

- [ ] Fazer a primeira prova em memoria
  - trabalhar sobre as cerca de 338 familias antes de adicionar `pgvector`
  - pre-gerar embeddings por comando operacional reproduzivel
  - medir inicializacao, memoria e latencia por consulta

- [ ] Criar porta de recuperacao desacoplada
  - entrada: mensagem atual e contexto permitido
  - saida: familia canonica, identificador, score, margem e origem do documento
  - limitar a `top-k` pequeno
  - permitir trocar a implementacao em memoria no futuro

- [ ] Aplicar politica deterministica de confianca
  - executar somente depois de alias exato e fuzzy
  - calibrar score minimo e margem entre primeiro e segundo candidato
  - distinguir sem candidato, candidato forte e candidatos ambiguos
  - nunca liberar busca ERP ou compatibilidade veicular apenas pelo embedding

### 3.3 Confirmacao sem depender obrigatoriamente da LLM

- [ ] Gerar pergunta de confirmacao por template do backend
  - exemplo: `Voce procura amortecedor, mola ou outra peca?`
  - gerar `options` somente a partir dos candidatos aprovados
  - impedir qualquer familia fora do conjunto recuperado
  - usar LLM para redacao apenas se um benchmark provar ganho de qualidade que justifique a latencia

- [ ] Estender `ConversationState` de forma retrocompativel nos dois servicos
  - adicionar `semantic_disambiguation` opcional
  - guardar texto original, candidatos, tentativa, modelo e versao do embedding
  - atualizar schemas do `docker-agent` e `docker-comm`
  - aceitar respostas antigas sem o novo campo

- [ ] Reutilizar exclusivamente o Redis existente
  - continuar usando `conv:{conversation_id}:history` e `conv:{conversation_id}:state`
  - deixar o agent produzir o estado e o comm persisti-lo
  - respeitar TTL e limite de historico atuais
  - nao criar nova instancia, chave paralela ou store no agent

- [ ] Tratar o ciclo multi-turno completo
  - confirmar por nome ou numero
  - refinar uma resposta descritiva
  - tratar negacao, `nenhuma dessas` e mudanca de assunto
  - limpar o estado ao confirmar, reiniciar ou realizar handoff
  - limitar tentativas para evitar loop

### 3.4 Observabilidade e rollout

- [ ] Registrar evidencia semantica na fila de revisao
  - guardar modelo, candidatos, scores, margens e familia confirmada
  - distinguir sugestao vetorial de confirmacao do usuario
  - nao promover automaticamente a primeira sugestao ao dataset formal

- [ ] Criar testes unitarios, de contrato e multi-turno
  - preferencia de alias/fuzzy sobre embedding
  - timeout ou indisponibilidade mantendo o fluxo atual
  - serializacao no Redis pelos contratos existentes
  - confirmacao seguida de modelo, ano e motor
  - `nenhuma dessas` pedindo nova descricao

- [ ] Fazer rollout por feature flag
  - iniciar desativado
  - executar primeiro em modo `shadow`
  - medir confirmacao, rejeicao, falso positivo, handoff e latencia
  - promover somente se melhorar pedidos genericos sem regredir pedidos explicitos

Deixar fora da primeira fase:

- embeddings para todos os itens do ERP
- substituicao do ranking lexical do ERP
- compatibilidade semantica entre peca e veiculo
- preenchimento de `part_query` sem confirmacao
- banco vetorial separado
- `pgvector` antes de a prova em memoria justificar persistencia

## Prioridade 4 - Otimizar somente o volume residual de LLM

Esta prioridade comeca depois de medir os efeitos do `deterministic_ask` e da recuperacao semantica.

- [ ] Medir o volume residual
  - contar chamadas, p50, p95 e erros por `pre_search_path`
  - separar casos contextuais, fora do dominio e ambiguidades reais
  - identificar quais casos ainda justificam uma LLM de 7B

- [ ] Benchmarkar GPU no Ollama
  - repetir os mesmos casos e modelo usados no baseline em CPU
  - confirmar uso real de VRAM em `/api/ps`
  - medir ganho com modelo carregado e apos cold start
  - comparar custo operacional com a quantidade residual de chamadas

- [ ] Comparar alternativas de inferencia
  - modelo menor ou mais rapido
  - quantizacao mais agressiva
  - tamanho do prompt e `LLM_NUM_PREDICT`
  - configuracao de threads/CPU quando GPU nao estiver disponivel
  - manter `LLM_KEEP_ALIVE=1h` enquanto nao houver evidencia de cold start relevante
  - preservar contrato JSON, qualidade conversacional e regras backend

- [ ] Avaliar cache somente onde houver chave e invalidacao seguras
  - priorizar embeddings de documentos e interpretacoes sem contexto conversacional
  - nao reutilizar resposta de LLM usando apenas o texto quando historico ou estado puderem mudar a decisao
  - medir taxa de acerto, economia real e risco de resposta obsoleta

- [ ] Decidir com benchmark de produto
  - nao promover configuracao que apenas reduza tempo e piore decisao, criterios ou pergunta
  - registrar a configuracao vencedora e manter rollback simples

## Prioridade 5 - Executar o ciclo de fine-tuning na maquina com GPU

O fine-tuning permanece posterior as correcoes estruturais e nao deve ser usado para corrigir catalogo, ranking ou orquestracao.

### 5.1 Preparacao antes do home office

- [ ] Validar o bootstrap completo em banco descartavel
  - conferir carga de `engine`, grupo, subgrupo, marca, modelo, aliases e regras
  - registrar o que nasce do repositorio e o que depende de dump externo

- [ ] Fazer backup e testar restore das tabelas dinamicas
  - `pre_search_review_interaction`
  - `pre_search_fine_tuning_dataset_header`
  - `pre_search_fine_tuning_dataset_record`
  - `pre_search_fine_tuning_run`

- [ ] Validar reproducao da stack
  - subir `ollama`, `presearch-db`, `docker-agent` e perfil `trainer`
  - validar modelo base, dataset exportado e acesso a GPU

- [ ] Preparar contingencia e transferencia
  - testar acesso remoto entre os PCs
  - definir transporte seguro de dump, dataset e adapter
  - manter copia recuperavel antes de qualquer mudanca de ambiente

### 5.2 Execucao na maquina com GPU

- [ ] Restaurar banco e validar conectividade dos containers
- [ ] Exportar e validar o dataset revisado
- [ ] Executar LoRA/QLoRA com `Qwen/Qwen2.5-7B-Instruct`
- [ ] Monitorar VRAM, tempo, perda de treino e artefatos
- [ ] Gerar `adapter` e `training_summary.json`
- [ ] Comparar candidato contra baseline no golden set e na bateria real

### 5.3 Retorno e promocao controlada

- [ ] Transportar adapter, resumo e manifestos para a empresa
- [ ] Testar importacao/publicacao no Ollama da empresa
- [ ] Promover somente se o candidato superar o baseline sem regressao critica
- [ ] Documentar rollback, restauracao e modelo final escolhido
- [ ] Registrar a run em `pre_search_fine_tuning_run`

## Hipoteses Adiadas

- [ ] Avaliar classificador auxiliar em portugues para slot filling
  - considerar `BERTimbau` ou equivalente somente se regras, fuzzy e embeddings deixarem uma lacuna mensuravel
  - nao adicionar nova camada apenas para substituir uma heuristica simples

- [ ] Avaliar `pgvector`
  - somente depois de a prova semantica em memoria comprovar ganho e necessidade de persistencia

- [ ] Criar seed incremental e rotinas de carga
  - executar quando houver necessidade operacional clara alem do bootstrap consolidado
