# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 02/10/2026. A ordem abaixo prioriza fine-tuning, integracoes, avaliacao comercial e operacao.

## Ordem De Execucao

1. Preparar e executar fine-tuning controlado em GPU.
2. Retomar a avaliacao comercial e a divida deterministica registrada na Prioridade 4.5.
3. Avaliar recuperacao semantica e otimizacoes com dados reais.

O backend e o catalogo permanecem a autoridade final. Caminhos deterministicos atendem fatos catalogados; a LLM trata linguagem residual e nunca libera busca sem gates e proveniencia.

## Prioridade 3 - GPU E Fine-Tuning Controlado

- [ ] Configurar Ollama principal na GPU e fallback local
  - conexao privada, timeout, retry, circuito de falhas, telemetria de provedor/fallback e handoff quando ambos falharem.
- [ ] Corrigir benchmark e proteger os splits
  - reprovar slots extras, codigos sem evidencia e contexto incorreto; congelar teste retido e ampliar cobertura de negacao, multi-item, motor textual, `nao sei` e handoff.
- [ ] Alinhar exportacao, benchmark e runtime ao mesmo contrato
  - compartilhar montagem de payload e versionar prompt, estado e regras.
- [ ] Validar trainer em GPU descartavel
  - conferir CUDA/VRAM, dependencias, tokenizer, truncamento, perda, mascara e checkpoints.
- [ ] Executar LoRA/QLoRA com `Qwen/Qwen2.5-7B-Instruct`
  - salvar adapter, checkpoints e manifest fora da GPU; comparar baseline/candidato; validar Ollama sem substituir o ativo; promover apenasquai com criterios aprovados e rollback documentado.

## Prioridade 5 - Recuperacao Semantica E Operacao

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

- [ ] Avaliar o envio opcional de `last_messages` da Convert como contexto para o agente
  - Manter `last_message` como a mensagem atual; usar `last_messages`, que contem somente mensagens recebidas do cliente, apenas para recuperar contexto anterior a entrada no fluxo da IA e completar um pedido enviado em varias mensagens curtas.
  - Nao transformar o texto concatenado em uma nova mensagem atual nem duplicar mensagens no historico Redis; remover a mensagem corrente se ela tambem vier incluida no contexto.
  - Definir limites e precedencia para que correcoes recentes prevalecam e mensagens antigas de outro pedido nao contaminem a busca; comparar o beneficio com o historico que o `docker-comm` ja mantem por conversa.
  - Antes de implementar, validar formato, ordem e janela real da variavel na Convert; cobrir exemplo como `ola` + pedido de peca/veiculo + ano/motor e garantir compatibilidade com o contrato atual.
- [ ] Avaliar classificador auxiliar em portugues somente se regras e embeddings deixarem lacuna mensuravel.
- [ ] Avaliar `pgvector` somente depois da prova semantica em memoria.
