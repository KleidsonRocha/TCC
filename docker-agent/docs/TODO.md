# TODO - Backlog Priorizado Do Produto (docker-agent)

Este arquivo contem somente trabalho ainda pendente. Entregas concluidas,
evidencias e decisoes historicas ficam em `PROGRESS.md`, `DECISIONS.md` e
`PROBLEMAS_E_SOLUCOES.md`.

## Ordem recomendada

1. estabilizar a stack convencional na VPS;
2. criar fallback para indisponibilidade da GPU;
3. medir a GPU e executar o fine-tuning;
4. fechar pendencias funcionais do ERP e multi-turno;
5. integrar o WhatsApp;
6. avaliar recuperacao semantica/RAG;
7. otimizar custos e infraestrutura somente com evidencias.

Regra geral: caminhos deterministas continuam sendo a primeira opcao. A LLM
fica reservada para linguagem incerta, contexto ambiguo e casos fora das regras.

## Criterio obrigatorio para cada bloco

Toda prioridade implementada deve:

- transformar casos reais afetados em regressao automatizada;
- executar testes focados e a suite completa;
- medir `pre_search_path` e `stage_latency_ms` quando tocar runtime;
- reexecutar os casos correspondentes da bateria real;
- comparar qualidade e latencia antes/depois;
- atualizar `PROGRESS.md`, `DECISIONS.md` e o fluxo runtime quando houver mudanca arquitetural;
- manter rollback e backup antes de alterar ambiente ou modelo.

## Prioridade 0 - Estabilizar a aplicacao na VPS

Objetivo: deixar a aplicacao convencional funcionando sem depender da GPU.

- [ ] Subir e validar a stack no VPS KVM 4
  - `docker-comm`, `docker-agent`, Redis, PostgreSQL, Streamlit;
  - Ollama local opcional para fallback.
- [ ] Configurar a conectividade com o ERP externo
  - usar `ERP_DB_HOST=186.250.95.113` e `ERP_DB_PORT=5430`;
  - manter `CATALOG_DB_HOST=presearch-db` e `CATALOG_DB_PORT=5432` para o banco local;
  - testar a conexao a partir da VPS, cujo IP de origem autorizado e `72.61.47.31`;
  - manter SSL, credenciais fortes e timeout de conexao do ERP;
  - documentar que `186.250.95.113:5430` e um redirecionamento externo, nao um novo banco local.
- [ ] Validar `docker compose up -d` em ambiente limpo
  - conferir variaveis do `.env`, portas e healthchecks;
  - confirmar persistencia do banco e do Redis apos reinicio.
- [ ] Endurecer a exposicao de portas da stack
  - publicar externamente somente as portas necessarias para o proxy reverso;
  - restringir ou remover bindings publicos de Redis, PostgreSQL, Ollama e APIs internas;
  - confirmar firewall da VPS e regra de origem para o acesso ao ERP;
  - nao abrir a porta `5430` no Nginx: ela e uma conexao de saida para o banco externo.
- [ ] Configurar Nginx como entrada HTTP/HTTPS
  - apontar o dominio para a VPS e emitir certificado TLS;
  - encaminhar a interface para o Streamlit (`127.0.0.1:8501`);
  - encaminhar a API/webhook para o `docker-comm` (`127.0.0.1:8000`);
  - preservar headers de host, proxy e WebSocket quando usados pelo Streamlit;
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

- [ ] Resolver pendencias individualmente em pedidos multi-item
  - guardar `active_item_index` quando faltar criterio em um item;
  - retomar somente o item pendente depois da resposta;
  - limpar o item ao concluir, negar ou mudar de assunto.
- [ ] Corrigir follow-up com motor textual
  - reconhecer `zetec rocam`, `duratec`, `duratec he`, `sigma`, `ea111`,
    `ea211` e equivalentes catalogados;
  - validar contra opcoes do modelo quando houver lista conhecida;
  - revalidar `coxim amortecedor ecosport 2008 -> zetec rocam`.
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
  - reduzir ruido de tampa, mangueira, kit, parafuso e lampada;
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
  - medir `top-1`, `top-3`, empates e `no_match`.

## Prioridade 3 - Fine-tuning controlado

O dataset revisado ja foi promovido e exportado. O ultimo balanceamento gerou
122 exemplos de treino, 15 de validacao e 15 de teste. O conjunto de teste deve
permanecer retido.

- [ ] Validar reproducao do trainer em uma instancia GPU descartavel
  - imagem, dependencias, acesso ao Hugging Face, CUDA/VRAM e artefatos.
- [ ] Executar LoRA/QLoRA com `Qwen/Qwen2.5-7B-Instruct`
- [ ] Salvar adapter, checkpoints, manifest e resumo fora da GPU
- [ ] Comparar modelo base e candidato no golden set, teste retido e bateria real
- [ ] Publicar candidato no Ollama somente se superar o baseline
- [ ] Registrar a run em `pre_search_fine_tuning_run`
- [ ] Documentar rollback para o modelo anterior.

## Prioridade 4 - Integrar WhatsApp

Somente iniciar depois de a VPS, o proxy reverso e o fallback estarem estaveis.

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

## Hipoteses adiadas

- [ ] Avaliar classificador auxiliar em portugues somente se regras e embeddings
  deixarem uma lacuna mensuravel.
- [ ] Avaliar `pgvector` somente depois da prova semantica em memoria.
- [ ] Criar seeds incrementais somente quando houver necessidade operacional
  alem do bootstrap consolidado.
