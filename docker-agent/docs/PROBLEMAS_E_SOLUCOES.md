# Historico Consolidado de Problemas e Solucoes

Este documento registra os principais problemas identificados durante a evolucao
do projeto, a solucao adotada, a evidencia disponivel e o que ainda permanece
pendente. Ele complementa `PROGRESS.md`, `DECISIONS.md` e `TODO.md`: o objetivo
daqui e preservar a linha de raciocinio tecnica, e nao substituir o backlog.

## 1. Arquitetura e responsabilidades

### Problema

Uma mensagem informal precisava ser convertida em criterios de busca para o
ERP, mas a fronteira entre regra de catalogo, LLM, historico conversacional e
busca comercial nao estava suficientemente explicita.

### Solucao

O fluxo foi consolidado em camadas:

1. `docker-comm` recebe a mensagem e reutiliza o Redis para historico e
   `ConversationState`.
2. `docker-agent` extrai criterios deterministas e consulta o catalogo no
   Postgres.
3. Regras e gates determinam se o caso pode seguir sem LLM.
4. A LLM recebe apenas os casos que exigem interpretacao linguistica ou
   ambiguidade residual.
5. O ERP e consultado somente depois da validacao do contrato.
6. A resposta e o estado atualizado voltam ao `docker-comm` e ao Redis.

Essa organizacao preserva o escopo do projeto: a LLM interpreta linguagem, mas
nao substitui a fonte de verdade comercial nem as regras de seguranca.

## 2. `part_code` inventado

### Problema

O caso real `FREIO-2010` mostrou que o modelo podia transformar modelo/ano ou
descricao de peca em um codigo de produto inexistente.

### Solucao

Foi criada uma validacao defensiva de proveniencia. Um `part_code` somente pode
ser aceito quando:

- aparece literalmente na mensagem atual;
- aparece em uma mensagem anterior do usuario;
- e validado pelo extractor determinista;
- ou e confirmado por uma fonte explicita do sistema.

O modelo nao pode fabricar um codigo a partir de `Gol 2010`, nome de familia,
ano, motor ou qualquer combinacao sem evidencia literal.

### Evidencia

- regressao para `pastilha de freio 2010 1.0`;
- testes de regras e de resposta;
- contrato e provenance preservados no export de fine-tuning.

## 3. Regras de catalogo que geravam perguntas sem sentido

### Problema

Algumas familias herdavam campos obrigatorios incorretos, levando o sistema a
perguntar eixo ou lado para produtos que nao usam esses criterios.

### Solucao

As regras foram corrigidas na fonte de verdade do bootstrap e nos CSVs:

- filtro de oleo: nao exige eixo;
- filtro de ar do motor: nao exige eixo;
- filtro de combustivel: nao exige lado;
- bicos injetores: nao exigem lado esquerdo/direito;
- velas de ignicao: nao exigem lado;
- aditivos: nao exigem lado;
- anti-chama: tratado como aplicacao no motor, sem eixo;
- lubrificantes/oleos: podem ser buscados por viscosidade/codigo, como `20W50`;
- marcas como NGK sao preferencias, mantendo possibilidade de similares.

### Evidencia

O bootstrap consolidado e os testes de catalogo passaram a cobrir as familias
obrigatorias e casos similares auditados.

## 4. Caminho deterministico para buscas completas

### Problema

Pedidos completos dependiam desnecessariamente da LLM, aumentando latencia e
variabilidade.

### Solucao

Foi implementado o `deterministic_bypass` para casos em que extractor,
catalogo, criterios e regras ja determinam uma busca segura. O caminho:

- preserva canonizacao e proveniencia;
- nao altera o ranking ERP;
- mantem fallback imediato para a LLM quando houver duvida;
- possui feature flag independente;
- registra `tool_trace.pre_search_path` e latencia por etapa.

## 5. Caminho `deterministic_ask`

### Problema

Casos obvios e incompletos ainda chamavam a LLM para formular uma pergunta que
o backend ja conhecia, por exemplo `radiador gol 2010` sem motor.

### Solucao

Foi criado um gate conservador que libera `ask` somente quando:

- a familia foi encontrada por alias exato ou o pedido e explicitamente
  automotivo sem familia;
- o catalogo conhece o campo ausente;
- `missing_fields`, `NextQuestion` e opcoes sao governados pelo backend;
- nao existe sintoma, descricao funcional, mudanca de assunto, handoff,
  candidato fuzzy inseguro ou slot pendente ambiguo.

O mesmo `ConversationState` continua sendo enviado ao `docker-comm` e salvo no
Redis. A LLM e chamada imediatamente quando qualquer criterio de elegibilidade
falha.

### Evidencia

O caminho e identificado separadamente na telemetria e a comparacao realizada
mostrou migracao de casos elegiveis de `llm` para `deterministic_ask`.

## 6. Latencia e infraestrutura

### Problema

Era necessario saber se o custo estava no pre-search, na busca ERP ou na
montagem da resposta antes de decidir por GPU, prompt menor ou outro modelo.

### Solucao

Foram separadas as metricas de:

- `pre_search_validator`;
- `search_parts`;
- `response_assembly`.

O benchmark diferencia os caminhos deterministas do caminho dependente da LLM.
GPU, `LLM_KEEP_ALIVE` e troca de modelo ficaram como decisoes posteriores ao
bypass, condicionadas aos numeros reais.

## 7. Respostas `no_match`

### Problema

Uma ausencia de resultado no ERP podia ser confundida com criterio insuficiente
ou conflitante, levando a mensagens que afirmavam incompatibilidade sem prova.

### Solucao

O contrato passou a distinguir:

- ausencia real de produto depois de pesquisar os criterios informados;
- criterios ainda insuficientes;
- criterios conflitantes;
- necessidade de nova tentativa ou handoff.

O `conversation_state` evita pedir novamente modelo, ano ou motor ja
informados e a resposta informa quais criterios foram efetivamente pesquisados.

## 8. Desambiguacao de muitos resultados

### Problema

Uma lista extensa de candidatos nao ajudava o usuario a escolher e nao havia
um estado funcional claro para a interacao seguinte.

### Solucao

Foi implementado `result_disambiguation` como estado multi-turno deterministico:

- seleciona o melhor discriminador seguinte entre aplicacao, versao, motor,
  lado, posicao e outros atributos;
- aceita selecao por numero, codigo, titulo ou atributo;
- trata negacao, mudanca de assunto e novas tentativas;
- encaminha depois do limite de tentativas;
- reutiliza os candidatos e o estado existentes no Redis, sem store paralelo.

## 9. Estado conversacional e Streamlit

### Problema

No ambiente copiado para outro computador, o Streamlit recarregava e trocava o
ID da conversa durante follow-ups.

### Diagnostico

Os eventos do Docker mostraram `exitCode=139` no `docker-comm-ui`, indicando
encerramento do processo e reinicio pelo Compose. A diferenca observada entre
as maquinas estava no conjunto de metricas, especialmente `pyarrow` 25 versus
24, e nao em uma nova conversa criada pelo Redis.

### Solucao operacional

O fluxo correto continua sendo manter o mesmo `conversation_id`, gravar
historico/estado no Redis e investigar o processo do container quando houver
reinicio. A combinacao de versoes das dependencias deve ser fixada no ambiente
de execucao para evitar divergencia entre maquinas.

## 10. Revisao humana e conversas multi-turno

### Problema

Era necessario revisar conversas reais, inclusive aquelas com varias pecas e
varios turnos, sem perder contexto ou marcar a conversa inteira de forma
incorreta.

### Solucao

Foi criada a aba de revisao de IA no Streamlit:

- agrupa por `conversation_id`;
- exibe a conversa completa em ordem cronologica;
- permite revisar um turno por vez;
- registra decisao, criterios, campos ausentes, pergunta e observacoes;
- suporta `reviewed_items` para pedidos com varias pecas;
- permite reabrir revisoes, mantendo historico em
  `pre_search_review_revision`;
- diferencia `pending`, `reviewed`, `discarded` e `promoted`.

Uma revisao nao vira dado de treino automaticamente: a promocao continua sendo
uma segunda barreira de qualidade.

## 11. Dataset supervisionado e exportacao

### Problema

O dataset precisava ser derivado de revisoes humanas, manter o contrato JSON e
ser transportavel para outra maquina de treinamento.

### Solucao

O fluxo formal passou a ser:

1. capturar interacoes em `pre_search_review_interaction`;
2. revisar no Streamlit;
3. promover somente casos revisados;
4. exportar `messages.jsonl` e `records.jsonl`;
5. rebalancear treino, validacao e teste sem separar conversas;
6. treinar o adapter fora do runtime da API.

O exportador tambem normaliza snapshots antigos que tinham `missing_fields` ou
pergunta stale em exemplos cujo alvo era `search`, registrando a normalizacao
no metadata sem alterar silenciosamente a revisao original.

### Estado validado

O dataset `pre-search-ft-v1` foi exportado com:

- 122 exemplos de treino;
- 15 exemplos de validacao;
- 15 exemplos de teste;
- codificacao UTF-8 validada;
- 13 testes direcionados do formato/exportador passando.

O conjunto de teste deve permanecer retido e ser avaliado junto ao golden set,
sem ser usado para ajustar o adapter.

## 12. O que continua pendente

As correcoes acima nao significam que todo o backlog foi encerrado. Permanecem
como proximas etapas:

- executar o primeiro treino LoRA/QLoRA com GPU;
- comparar base e adapter no golden set e no conjunto de teste retido;
- promover o adapter somente se houver ganho real sem regressao;
- aumentar a bateria de conversas reais e revisar novos casos;
- medir o volume residual de chamadas LLM antes de alterar infraestrutura;
- evoluir a busca semantica/RAG como trilha separada, sem substituir as regras
  deterministicas e o estado Redis;
- manter auditoria de catalogo e regras conforme novos produtos entram no ERP.

## 13. Evidencias e fontes

- `PROGRESS.md`: estado operacional e resultados de benchmark;
- `DECISIONS.md`: justificativas arquiteturais e limites dos caminhos;
- `TODO.md`: backlog restante e prioridades;
- `guide/pre_search_runtime_flow.md`: fluxo runtime e estados;
- `training/pre_search_fine_tuning.md`: revisao, promocao, exportacao e treino;
- `scripts/training/rebalance_pre_search_fine_tuning_dataset.py`: rebalanceamento
  deterministico dos splits.
