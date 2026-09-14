# TODO - Backlog Priorizado Do Produto (docker-agent)

Este arquivo contem somente trabalho ainda pendente. Entregas concluidas,
evidencias e decisoes historicas ficam em `PROGRESS.md`, `DECISIONS.md` e
`HISTORICO.md`.

Revisado em 14/09/2026: as correcoes de follow-up de ano/direcao, da regra de
`coxins` (posicao) e de `pastilhas de freio` (sem motor obrigatorio), alem dos
casos adicionados ao golden set, estao registradas em
[PROGRESS.md](PROGRESS.md#follow-ups-deterministicos-corrigidos-em-11092026).
As alteracoes mais recentes foram validadas localmente; sua aplicacao na VPS
ainda precisa ser confirmada. Os itens abaixo descrevem somente o restante.

## Ordem recomendada

1. corrigir os bloqueadores de busca, conversa, disponibilidade e acesso da Prioridade 0;
2. validar a stack na VPS e fechar as pendencias funcionais da Prioridade 2;
3. criar fallback para indisponibilidade da GPU e medir a inferencia;
4. fortalecer a avaliacao e executar o fine-tuning controlado;
5. integrar o WhatsApp;
6. avaliar recuperacao semantica/RAG;
7. otimizar custos e infraestrutura somente com evidencias.

Regra geral: caminhos deterministas continuam sendo a primeira opcao. A LLM
fica reservada para linguagem incerta, contexto ambiguo e casos fora das regras.

As correcoes abaixo incorporam a
[auditoria tecnica de 11/09/2026](HISTORICO.md#auditoria-especialista-de-11092026).
Os achados classificados como P1 no relatorio entram como bloqueadores na
Prioridade 0 deste backlog. Os casos e executores de reproducao estao vinculados
no historico e neste backlog. Fine-tuning, GPU e ranking nao substituem essas correcoes.

## Criterio obrigatorio para cada bloco

Toda prioridade implementada deve:

- transformar casos reais afetados em regressao automatizada;
- executar testes focados e a suite completa;
- medir `pre_search_path` e `stage_latency_ms` quando tocar runtime;
- reexecutar os casos correspondentes da bateria real;
- comparar qualidade e latencia antes/depois;
- atualizar `PROGRESS.md`, `DECISIONS.md` e o fluxo runtime quando houver mudanca arquitetural;
- manter rollback e backup antes de alterar ambiente ou modelo.

## Prioridade 0 - Corrigir bloqueadores e estabilizar a aplicacao

Objetivo: preservar a intencao e a aplicacao de cada peca e deixar a aplicacao
convencional funcionando antes de liberar atendimento autonomo a clientes.
Preparar a VPS pode ocorrer em paralelo, mantendo a stack isolada ate a validacao.

### Identidade e compatibilidade na busca ERP

As correcoes de identidade, aplicacao, intervalos e acessorios foram implementadas
e validadas em 14/09/2026. Evidencias e golden sets em
[PROGRESS.md](PROGRESS.md#identidade-e-aplicacao-erp-corrigidas-em-14092026).

O SQL ja foi aplicado no banco quente pelo usuario. Em 14/09, a exportacao
somente de leitura confirmou as duas views v2: 52.798 itens e 1.779.443
aplicacoes. O snapshot versionado anterior conserva 1.776.907 aplicacoes;
a copia de verificacao ficou local, sem substituir os arquivos preparados no Git.

- [ ] Concluir a implantacao e validacao do contrato ERP v2 na VPS
  - conferir backup das definicoes externas e acesso da VPS ao banco quente;
  - atualizar o runtime da VPS e confirmar acesso aos dois objetos v2;
  - repetir o golden set ERP e os pedidos reais no backend externo;
  - manter o snapshot local v2 habilitado durante a migracao;
  - confirmar a propagacao dos cinco aliases novos de tampa/mangueira para o catalogo da VPS.

### Negacao, conflitos e pedidos com varias pecas

- [ ] Resolver negacoes e substituicoes antes de liberar o bypass de busca
  - `pastilha traseira do Gol 2010, nao dianteira` deve preservar `rear`;
  - `nao quero radiador, quero filtro de oleo Gol 2010 1.0` deve conter somente o filtro;
  - nao transformar clausulas negativas em itens de `items[]`;
  - bloquear bypass quando a negacao ou correcao ainda nao estiver resolvida;
  - pedir confirmacao para conflitos como `Honda Gol`, sem pesquisar a combinacao contraditoria.
- [ ] Preservar itens distintos e os dados de cada veiculo
  - corrigir a deduplicacao que usa somente familia, posicao e lado;
  - manter dois itens em `radiador Gol 2010 1.0 e radiador Corsa 2011 1.4`;
  - compartilhar contexto somente quando o mesmo veiculo estiver explicitamente associado;
  - impedir que motor, ano, marca ou modelo de uma clausula contaminem outra.
- [ ] Aplicar gate, canonizacao e proveniencia a cada item antes da consulta
  - recalcular campos obrigatorios e score para cada familia em `items[]`;
  - validar `part_code` de todos os itens contra evidencia do usuario;
  - rejeitar o codigo simulado `ZZ-12345` quando ele vier apenas da saida da LLM;
  - em `radiador Gol 2010 1.0 e bandeja Corsa 2011`, marcar a bandeja como
    incompleta enquanto faltar lado, sem copiar o motor do Gol;
  - nao liberar todos os itens porque o criterio principal esta completo.
- [ ] Resolver pendencias individualmente em pedidos multi-item
  - guardar `active_item_index` ou identificador equivalente do item pendente;
  - aplicar `esquerda` a bandeja pendente, sem alterar os criterios do radiador;
  - conservar os demais itens e seus resultados ao retomar o atendimento;
  - limpar ou substituir somente o estado afetado ao concluir, negar ou corrigir um item.
- [ ] Invalidar candidatos ao corrigir criterios durante a desambiguacao
  - detectar alteracoes de modelo, ano, motor, lado e demais filtros, mesmo sem troca de familia;
  - reproduzir `radiador Gol 2010 1.0 -> corrigindo, o carro e um Corsa 2011 1.4`;
  - descartar os candidatos do Gol, revalidar os dados e refazer a consulta do Corsa;
  - impedir selecao de candidatos obtidos com filtros anteriores.

### Erros operacionais, concorrencia e acesso

- [ ] Diferenciar indisponibilidade do ERP de busca sem resultados
  - nao converter `SearchPartsServiceUnavailableError` em HTTP 200 com `no_match`;
  - propagar HTTP 503 no fluxo de item unico, conforme o contrato de indisponibilidade;
  - preservar `error` por item nos pedidos multiplos e permitir nova tentativa;
  - distinguir falha e ausencia na resposta, telemetria e captura para revisao.
- [ ] Remover I/O bloqueante do event loop da API
  - executar chamadas HTTP/PostgreSQL de forma assincrona ou fora do event loop;
  - definir limites de concorrencia e timeouts para inferencia e consulta;
  - tornar `_last_audit_info` local a requisicao antes de permitir execucoes concorrentes;
  - testar uma inferencia lenta junto de `/health` e de outra conversa deterministica;
  - comprovar que a requisicao lenta nao bloqueia as demais nem mistura auditorias.
- [ ] Exigir protecao administrativa antes da exposicao externa
  - exigir `REVIEW_API_KEY` ou autenticacao equivalente em producao;
  - impedir que ausencia de configuracao libere silenciosamente `/review/*`;
  - testar leitura, revisao, descarte, reabertura e promocao conforme os acessos previstos;
  - definir limites de tamanho para texto, historico, itens e candidatos recebidos;
  - restringir `/respond` ao gateway autorizado quando aceitar estado fornecido pelo chamador.
- [ ] Separar saude do processo de prontidao das dependencias
  - manter uma verificacao leve que responda durante inferencias;
  - informar indisponibilidade de catalogo, ERP ou inferencia sem declarar a stack pronta;
  - documentar timeouts e comportamento degradado de cada dependencia.

### Implantacao e reproducao na VPS

- [ ] Confirmar as ultimas correcoes de catalogo na stack ja instalada na VPS
  - sincronizar `coxins -> needs_position=true, needs_axle=false`;
  - sincronizar `pastilhas de freio -> needs_position=true, needs_engine=false`;
  - atualizar o agente e testar em conversas novas no site;
  - a stack e o fallback PostgreSQL ja funcionam na VPS; isso nao encerra a
    validacao funcional completa nem os bloqueadores de beta.
- [ ] Resolver a recusa de acesso ao ERP externo com a Optidata
  - endpoint `186.250.95.113:5430` configurado e conectividade TCP confirmada;
  - corrigir a recusa `no pg_hba.conf entry` para a origem `72.61.47.31`;
  - esclarecer e configurar TLS: o teste com `sslmode=require` informou que
    o servidor nao suporta SSL;
  - confirmar consulta autenticada e logs com backend `erp_postgres`;
  - o fallback local ja foi acionado com sucesso, mas nao comprova acesso ao ERP externo.
- [ ] Validar `docker compose up -d` em ambiente limpo
  - conferir variaveis do `.env`, portas e healthchecks;
  - confirmar persistencia do banco e do Redis apos reinicio.
- [ ] Endurecer a exposicao de portas da stack
  - publicar externamente somente as portas necessarias para o proxy reverso;
  - restringir ou remover bindings publicos de Redis, PostgreSQL, Ollama e APIs internas;
  - confirmar firewall da VPS e regra de origem para o acesso ao ERP;
  - nao abrir a porta `5430` no Nginx: ela e uma conexao de saida para o banco externo.
- [ ] Concluir a validacao do Nginx e preparar o futuro webhook
  - DNS e acesso ao Streamlit por `chat.clayforgestudio.com.br` ja demonstrados;
  - verificar certificado TLS, redirecionamento HTTPS e estabilidade do WebSocket;
  - encaminhar a futura API/webhook para o `docker-comm` (`127.0.0.1:8002`),
    pois a porta publica `8000` ja e utilizada pelo Portainer;
  - validar renovacao do certificado e comportamento apos reinicio da VPS.
- [ ] Fazer backup e restore do PostgreSQL e Redis
  - catalogo e regras;
  - fila de revisao;
  - dataset de fine-tuning;
  - estados conversacionais necessarios para recuperacao.
- [ ] Validar o fluxo completo sem GPU
  - busca deterministica, `deterministic_ask`, follow-up, `no_match`,
    desambiguacao e pedidos multi-item.
- [ ] Registrar checklist de deploy, parada, restauracao e verificacao de `/health`.
- [ ] Fechar a validacao de beta com evidencias
  - aprovar regressoes de todos os bloqueadores acima;
  - revisar uma amostra curada de aplicacoes e produtos retornados;
  - reexecutar conversas pela API e pelo `docker-comm`, incluindo persistencia no Redis;
  - registrar que sucesso HTTP e suite verde nao comprovam compatibilidade comercial.

## Prioridade 1 - Fallback e conexao com a GPU

Objetivo: usar a GPU como caminho principal sem tornar a aplicacao dependente dela.

- [ ] Configurar Ollama principal na instancia GPU
  - preferir conexao privada entre VPS e GPU;
  - nao expor Ollama publicamente sem autenticacao;
  - manter modelo e adapter em copia recuperavel.
- [ ] Implementar fallback de inferencia
  - `LLM_PRIMARY_BASE_URL` para GPU;
  - `LLM_FALLBACK_BASE_URL` para Ollama local;
  - timeout curto, retry controlado e circuito de falhas;
  - handoff controlado se os dois modelos falharem.
- [ ] Criar feature flag e telemetria do fallback
  - registrar `llm_provider` e `fallback_reason` no `tool_trace`.
- [ ] Escolher modelo local de contingencia
  - testar modelo de 1,5B a 3B na VPS;
  - preservar o mesmo contrato JSON e as regras de `part_code`.
- [ ] Medir tempo de conexao, cold start, p50/p95, timeouts e quedas.

## Prioridade 2 - Pendencias funcionais do fluxo

### Multi-item e follow-up

- [ ] Corrigir follow-up com motor textual
  - cobrir tambem a opcao sugerida `BE`, que foi ignorada no teste real de Corsa;
  - reconhecer `zetec rocam`, `duratec`, `duratec he`, `sigma`, `ea111`,
    `ea211` e equivalentes catalogados;
  - validar contra opcoes do modelo e intervalos de ano quando houver lista conhecida;
  - revalidar `radiador EcoSport 2008 -> zetec rocam` e
    `coxim amortecedor ecosport 2008 -> zetec rocam`;
  - nao repetir a pergunta ignorando uma motorizacao textual informada.
- [ ] Dar continuidade util quando o cliente responder `nao sei`
  - usar outro discriminador com evidencia ou oferecer atendimento humano;
  - limitar repeticoes de perguntas sem progresso;
  - cobrir `radiador Gol 2010 -> nao sei a motorizacao`.
- [ ] Corrigir cobertura lexical de pecas e marcas comerciais
  - reconhecer `4 velas NGK para Gol 2010 1.0`, preservando familia, quantidade e marca;
  - governar aliases comerciais no catalogo, evitando lista restrita codificada no extractor;
  - manter `preferred_product_brand` separado de marca do veiculo e de compatibilidade.
- [ ] Confirmar a familia antes de assumir uma descricao funcional ou sintoma
  - `peca que evita o carro ficar pulando depois de um buraco` nao deve fixar `bracos`
    sem evidencia ou confirmacao;
  - pedir esclarecimento com candidatos controlados ou encaminhar o atendimento;
  - implementar essa protecao no fluxo atual, independentemente da futura camada semantica.
- [ ] Tratar pedido de vendedor e sintomas com motivo de resposta adequado
  - encaminhar pedido explicito de vendedor sem aguardar inferencia desnecessaria;
  - nao apresentar sintoma ou pedido de atendimento como familia inexistente no catalogo;
  - preservar os dados do carro ao encaminhar.
- [ ] Reestruturar o prompt residual da LLM como contrato operacional
  - aplicar somente aos casos nao resolvidos deterministicamente;
  - definir precedencia entre mensagem atual, mensagens do usuario,
    `ConversationState`, seed e historico;
  - tratar mensagens do assistant apenas como contexto;
  - manter backend como autoridade final.
- [ ] Padronizar perguntas e respostas publicas
  - `side` = esquerdo/direito;
  - `position` = dianteiro/traseiro;
  - `axle` somente quando a familia exigir;
  - perguntas curtas e especificas.
  - a extracao e a busca por posicao ja aceitam `dianteiro/dianteira` e
    `traseiro/traseira`; ainda auditar equivalencia na desambiguacao e em
    campos direcionais restantes, sem confundir posicao com eixo.

### Busca e ranking ERP

- [ ] Reavaliar a desambiguacao apos busca com muitos itens
  - reproduzir na VPS as perguntas que surgem depois de `search` com varios candidatos;
  - escolher o proximo discriminador somente quando ele separar de fato os resultados
    retornados (aplicacao, versao, motor, lado, posicao ou outro atributo);
  - evitar perguntas genericas, repetidas ou sem relacao clara com a diferenca entre
    os itens apresentados;
  - quando nao houver discriminador confiavel, apresentar uma lista curta/paginada,
    permitir refinamento livre ou oferecer handoff, sem inventar nova restricao;
  - cobrir selecao, negacao, mudanca de assunto e limite de tentativas no mesmo
    `ConversationState`/Redis;
  - registrar casos reais e criar regressao para cada pergunta considerada sem sentido.
- [ ] Refinar ranking do ERP
  - partir dos filtros de identidade e aplicacao corrigidos na Prioridade 0;
  - reduzir empates e priorizar aplicacao exata;
  - revisar pesos de complemento, injecao, motor e transmissao.
- [ ] Melhorar apresentacao de texto e encoding
  - garantir UTF-8 nas mensagens publicas;
  - manter normalizacao interna separada do texto exibido;
  - revisar titulos e respostas sem alterar identidade ou ranking.
- [ ] Auditar familias compostas e quantidade
  - preservar `polia da bomba`, `kit corrente da bomba` e `junta do cabecote`;
  - confirmar quantidade somente com evidencia linguistica;
  - ignorar numeros de ano, motor, modelo e cilindrada.
- [ ] Reexecutar bateria real focada em ranking
  - medir `top-1`, `top-3`, candidatos incompatíveis, empates e `no_match`;
  - usar aplicacoes rotuladas por avaliador humano, alem de verificacoes do contrato.
- [ ] Definir o significado publico de `confidence`
  - nao apresentar constantes como probabilidade comprovada de encaixe;
  - separar confianca na extracao, relevancia da busca e confirmacao de aplicacao;
  - calibrar somente com dados rotulados e avaliacao apropriada.
- [ ] Explicitar o alcance comercial da busca por filial
  - documentar que `branch_id` ainda nao filtra a consulta atual;
  - nao afirmar preco ou disponibilidade com base somente em candidatos de catalogo;
  - definir integracao de estoque/preco por filial antes de oferecer essas respostas.

## Prioridade 3 - Fine-tuning controlado

O dataset revisado ja foi promovido e exportado. O ultimo balanceamento gerou
122 exemplos de treino, 15 de validacao e 15 de teste. O conjunto de teste deve
permanecer retido.

As correcoes da Prioridade 0 e os ajustes de avaliacao abaixo precedem o treino
e a promocao de um candidato. O teste retido nao deve orientar ajustes repetidos.

- [ ] Corrigir o benchmark para rejeitar respostas estruturalmente incorretas
  - verificar slots extras indevidos, inclusive `part_code` sem proveniencia;
  - comparar todos os itens, suas identidades, criterios e campos faltantes;
  - reprovar o caso simulado da auditoria que hoje aceita codigo inventado nao previsto;
  - avaliar correcao de contexto, loops, sucesso por conversa e numero de turnos;
  - distinguir JSON bruto conforme o contrato, saida corrigida por coercao e fallback.
- [ ] Ampliar cobertura e proteger os splits do dataset
  - incluir familias, negacoes, correcoes, motor textual, `nao sei` e pedidos multiplos;
  - incluir multi-item na validacao e `handoff` no teste retido, hoje ausentes;
  - manter conversas no mesmo split e procurar duplicatas, parafrases e vazamento de contexto;
  - congelar uma versao do teste antes do experimento e registrar sua composicao;
  - revisar explicitamente os casos sinteticos da auditoria antes de qualquer promocao.
- [ ] Alinhar exemplos exportados com o contrato do runtime
  - reproduzir `conversation_state`, `multi_item_rule` e a precedencia do contexto;
  - compartilhar a montagem do payload entre runtime, exportacao e benchmark;
  - atualizar e versionar o prompt dos exports antes do proximo treino.
- [ ] Validar tokenizacao, perda e frequencia de avaliacao do trainer
  - medir truncamento real com o tokenizer e garantir que a resposta completa participe do treino;
  - revisar `TRAINER_MAX_SEQ_LENGTH=1024` conforme a distribuicao dos exemplos;
  - configurar e verificar perda sobre a resposta desejada, com mascara de assistant quando suportada;
  - ajustar `eval_steps` e `save_steps` ao numero real de passos; os defaults de 50
    podem ultrapassar uma run de cerca de 32 passos com o dataset atual;
  - comprovar que houve avaliacao e selecao de checkpoint durante o treino.
- [ ] Validar reproducao do trainer em uma instancia GPU descartavel
  - imagem, dependencias, acesso ao Hugging Face, CUDA/VRAM e artefatos;
  - fixar versoes compativeis de dependencias, modelo base e tokenizer.
- [ ] Executar LoRA/QLoRA com `Qwen/Qwen2.5-7B-Instruct`
- [ ] Salvar adapter, checkpoints, manifest e resumo fora da GPU
- [ ] Comparar modelo base e candidato no golden set, teste retido e bateria real
- [ ] Validar o caminho de importacao do adapter no Ollama antes da promocao
  - testar arquitetura Qwen, modelo base correspondente e formato do artefato na versao fixada;
  - registrar se a importacao e direta ou exige conversao para GGUF;
  - comprovar inferencia com o candidato sem substituir o modelo ativo.
- [ ] Promover o candidato somente apos cumprir os criterios de qualidade
  - exigir golden set, teste retido e bateria de atendimento com limites para erros criticos;
  - impedir promocao apenas por ganho de latencia quando persistirem falhas criticas;
  - publicar para atendimento somente apos a comparacao aprovada com o baseline.
- [ ] Registrar a run em `pre_search_fine_tuning_run`
- [ ] Documentar rollback para o modelo anterior.

## Prioridade 4 - Integrar WhatsApp

Somente iniciar depois de os bloqueadores da Prioridade 0 estarem corrigidos
e de a VPS, o proxy reverso e o fallback estarem estaveis.

- [ ] Criar webhook `POST /webhooks/whatsapp` no `docker-comm`
- [ ] Implementar verificacao do webhook e autenticacao das chamadas
- [ ] Mapear telefone para `source=whatsapp`, `conversation_id` estavel e `branch_id`
- [ ] Enviar resposta pela API oficial da Meta
- [ ] Controlar mensagens duplicadas e reentregas
- [ ] Manter webhook em dominio estavel da VPS
- [ ] Usar o dominio estavel no cadastro da Meta
  - nao depender da URL temporaria de tunnel ou de uma instancia GPU;
  - manter o webhook apontando para o Nginx, que encaminha ao `docker-comm`;
  - revisar segredo de verificacao, token de acesso e rotacao de credenciais.
- [ ] Testar handoff, follow-up, multi-item e indisponibilidade da GPU
- [ ] Nao expor Redis, PostgreSQL ou Ollama diretamente na internet.

## Prioridade 5 - Recuperacao semantica para descricoes genericas

Esta etapa trata frases como `aquilo que segura o carro`, sintomas e descricoes
funcionais. Ela nao substitui catalogo, regras ou estado no Redis.

- [ ] Montar dataset semantico separado do fine-tuning
- [ ] Registrar baseline de `top-1`, `top-3`, falso positivo, handoff e latencia
- [ ] Criar documentos curados por familia real
- [ ] Comparar embeddings adequados para portugues
- [ ] Fazer primeira prova em memoria sobre familias catalogadas
- [ ] Criar porta de recuperacao com score, margem e proveniencia
- [ ] Aplicar politica conservadora: alias/fuzzy precedem embedding e embedding
  nunca libera busca ERP sozinho.
- [ ] Gerar confirmacao por template do backend
- [ ] Reutilizar exclusivamente `ConversationState` e Redis atuais
- [ ] Adicionar feature flag e rollout em modo shadow
- [ ] Promover somente se melhorar casos genericos sem regressao.

## Prioridade 6 - Otimizacao operacional

- [ ] Medir volume residual de LLM por `pre_search_path`
- [ ] Comparar GPU, modelo menor, quantizacao e `LLM_NUM_PREDICT`
- [ ] Manter `LLM_KEEP_ALIVE` enquanto cold start nao for gargalo
- [ ] Avaliar cache somente para casos sem contexto mutavel
- [ ] Configurar monitoramento de credito, GPU, memoria e latencia
- [ ] Definir politica de ligar/desligar GPU e backups automaticos
- [ ] Registrar custo mensal e custo por atendimento.
- [ ] Tornar atualizacoes de catalogo e snapshots reproduziveis
  - detectar drift entre CSV versionado e volume ativo;
  - definir atualizacao com backup e verificacao, preservando fila e dataset;
  - versionar e registrar checksum e data do snapshot local do ERP;
  - definir distribuicao do snapshot volumoso e politica de atualizacao/fallback;
  - fixar a versao da imagem Ollama em vez de depender de `latest`.
- [ ] Reduzir divergencia entre os caminhos de validacao
  - extrair politicas comuns de validacao por item e transicao de estado;
  - reduzir concentracao de responsabilidades no validador e no use case;
  - preservar contrato e comportamentos cobertos por regressao durante a refatoracao.
- [ ] Reconciliar documentacao com o estado verificado
  - revisar instrucoes antigas de treino, falhas de suite ja resolvidas e limites de escopo;
  - manter historico datado e separar evidencias atuais de resultados anteriores.

## Hipoteses adiadas

- [ ] Avaliar classificador auxiliar em portugues somente se regras e embeddings
  deixarem uma lacuna mensuravel.
- [ ] Avaliar `pgvector` somente depois da prova semantica em memoria.
- [ ] Criar seeds incrementais somente quando houver necessidade operacional
  alem do bootstrap consolidado.
