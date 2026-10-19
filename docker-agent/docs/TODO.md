# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 19/10/2026. A ordem abaixo prioriza avaliacao comercial, correcoes deterministicas e operacao. O experimento LoRA foi executado sem ganho global na configuracao avaliada; nova adaptacao e publicacao ficam em Hipoteses Adiadas, conforme [DECISIONS.md](DECISIONS.md#46-adiar-nova-adaptacao-do-modelo-apos-o-experimento-lora).

## Ordem De Execucao

1. Retomar a avaliacao comercial e as correcoes de catalogo, perguntas e filtros, incluindo a divida deterministica anteriormente registrada na Prioridade 4.5.
2. Avaliar recuperacao semantica separadamente, com dados curados e baseline.
3. Otimizar a operacao conforme telemetria e necessidade demonstrada.

O backend e o catalogo permanecem a autoridade final. Caminhos deterministicos atendem fatos catalogados; a LLM trata linguagem residual e nunca libera busca sem gates e proveniencia.

## Prioridade 5 - Recuperacao Semantica E Operacao

- [ ] Curar referencias e expectativas das auditorias de categoria de 14 e 19/10/2026.
  - Basear os lotes na [auditoria dos 371 casos do modelo base](../.tmp/eval/base_categories_review_20261019/analysis.md), com consulta somente leitura ao ERP e sondas no banco congelado. Ha 337 casos com referencia, mas 314 codigos distintos e 347 pedidos iniciais distintos. Separar pedidos naturais, titulos de catalogo adversariais, contradicoes e repeticoes de categoria/subcategoria.
  - Validar referencias de componente divergente, kits e classificacoes ERP; preservar a bateria original e versionar expectativas revisadas, sem promocao automatica a golden ou treino. Os 34 suspeitos nao sao uma taxa confirmada de falso negativo.
- [ ] Atualizar a VPS e validar o canal externo Omni/Convert com o lote de 19/10/2026.
  - Implantacao inicial restrita ao Docker local, conforme solicitado. Levar agente e gateway juntos, aplicar o atualizador transacional de catalogo e retestar Clio/Palio/S10, versoes completas e motor do FH 460; preservar volumes. Curadoria e refinamentos locais documentados em [PROGRESS.md](PROGRESS.md#curadoria-e-refinamentos-no-docker-local-em-19102026).
- [ ] Reexecutar bateria revisada e controles positivos/negativos no mesmo snapshot apos cada lote.
  - Incluir os 133 casos antes rotulados coerentes, revisando expectativas quando houver contradicao/identidade incorreta; preservar cobertura e os 27 golden. Medir precisao dos itens, familias curadas atendidas, conclusao, loops, handoffs adequados, divergencias e latencia. Nao declarar ganho por retirar filtros indiscriminadamente ou apresentar mais itens.
- [ ] Revisar nove subcategorias do grupo ERP 24 ausentes do catalogo ativo.
  - A consulta de cobertura encontrou 335 produtos nessas entradas. Confirmar
    escopo comercial e curar nomes/aliases antes de ampliar o catalogo.

- [ ] Implantar a correcao de busca por viscosidade e retestar no Omni/Convert.
  - Rebuild do `docker-agent`; validar `quero o oleo 5w40`, `5W-40`, outro
    grau e codigo `TEX-3117`. Verificacoes locais em `PROGRESS.md`.

- [ ] Filtrar as opcoes sugeridas de motorizacao pelo ano informado.
  - No reteste da EcoSport 2008 em 01/10/2026, a pergunta ofereceu `DRAGON` e `SIGMA`; o CSV versionado so registra `DRAGON` a partir de 2017 e `SIGMA` a partir de 2012 para esse modelo.
  - A aceitacao da resposta ja considera os intervalos, mas `_engine_options_for_model` apresenta todas as opcoes do modelo. Aplicar o mesmo criterio de ano a exibicao e cobrir a pergunta e a resposta com regressao.
- [ ] Montar prova semantica separada para descricoes genericas
  - dataset curado por familia, baseline de recuperacao, embeddings em portugues, score/margem/proveniencia, feature flag e modo shadow; embedding nunca libera busca ERP sozinho.
- [ ] Otimizar com telemetria real
  - medir caminho residual da LLM, GPU, latencia, memoria, creditos e custo por atendimento; avaliar cache somente sem contexto mutavel.
- [ ] Tornar atualizacoes de catalogo e snapshots reproduziveis
  - detectar drift, registrar checksum/data, versionar distribuicao e testar atualizacao com backup/verificacao.
- [ ] Reduzir divergencia entre caminhos de validacao e reconciliar documentacao com o estado verificado.

## Hipoteses Adiadas

### Nova Adaptacao E Publicacao Do Modelo

O experimento LoRA em BF16 foi concluido e preservado; nao usou QLoRA 4-bit.
Resultados e limites estao em [HISTORICO.md](HISTORICO.md#experimento-lora-em-gpu-de-19102026).
Os itens abaixo sao requisitos pendentes para eventual retomada, nao entregas
concluidas nem prioridades atuais. Retomar somente com lacuna residual da
LLM comprovada por revisao humana e criterio de ganho definido.

- [ ] Reavaliar Ollama principal na GPU e fallback local se a latencia/custo residual justificar.
  - Validar conexao privada, timeout, retry, circuito de falhas, telemetria de provedor/fallback e handoff quando ambos falharem. O experimento usou Transformers/PEFT por tunel temporario, sem implantar essa arquitetura.
- [ ] Antes de outra comparacao ou promocao de candidato, endurecer benchmark e proteger splits.
  - Reprovar slots extras, codigos sem evidencia e contexto incorreto; congelar teste retido independente por conversa e ampliar negacao, multi-item, motor textual, `nao sei` e handoff. Tratar as seis coincidencias exatas entre golden e treino; os outros 21 casos nao comprovam independencia de parafrases.
- [ ] Antes de novo treino, concluir a paridade entre exportacao, benchmark e runtime.
  - Compartilhar montagem de payload e versionar prompt, estado e regras, com regressao de paridade. Componentes existentes nao comprovam alinhamento integral.
- [ ] Complementar a auditoria do trainer se houver novo experimento.
  - CUDA, dependencias, carregamento do tokenizer, treino, perda e checkpoints funcionaram. Ainda auditar tokens supervisionados, mascara de perda e truncamento, incluindo conclusao do JSON alvo; distinguir limite de sequencia no treino do limite de saida na inferencia.
- [ ] Reavaliar outro LoRA/QLoRA e a publicacao do candidato no Ollama somente apos essas pre-condicoes.
  - Base e adapter atuais estao preservados localmente. A importacao/execucao do adapter no Ollama continua sem validacao. Definir criterios de ganho, salvar artefatos fora da GPU e validar candidato separado do ativo; promover somente se aprovado, com rollback documentado. Nao repetir automaticamente o mesmo treino nem aumentar apenas o limite do candidato para declarar ganho.

### Outras Hipoteses

- [ ] Avaliar o envio opcional de `last_messages` da Convert como contexto para o agente
  - Manter `last_message` como a mensagem atual; usar `last_messages`, que contem somente mensagens recebidas do cliente, apenas para recuperar contexto anterior a entrada no fluxo da IA e completar um pedido enviado em varias mensagens curtas.
  - Nao transformar o texto concatenado em uma nova mensagem atual nem duplicar mensagens no historico Redis; remover a mensagem corrente se ela tambem vier incluida no contexto.
  - Definir limites e precedencia para que correcoes recentes prevalecam e mensagens antigas de outro pedido nao contaminem a busca; comparar o beneficio com o historico que o `docker-comm` ja mantem por conversa.
  - Antes de implementar, validar formato, ordem e janela real da variavel na Convert; cobrir exemplo como `ola` + pedido de peca/veiculo + ano/motor e garantir compatibilidade com o contrato atual.
- [ ] Avaliar classificador auxiliar em portugues somente se regras e embeddings deixarem lacuna mensuravel.
- [ ] Avaliar `pgvector` somente depois da prova semantica em memoria.
