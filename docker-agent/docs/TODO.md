# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 30/09/2026. A ordem abaixo prioriza operacao segura, conversa, avaliacao comercial, fine-tuning e integracoes.

## Ordem De Execucao

1. Fechar a integracao do fluxo HTTP de conversacao com a Convert: recuperacao apos timeout e roteamento por etapa.
3. Preparar e executar fine-tuning controlado em GPU.
4. Integrar WhatsApp apos a beta estavel.
5. Retomar a avaliacao comercial e a divida deterministica registrada na Prioridade 4.5.
6. Avaliar recuperacao semantica e otimizacoes com dados reais.

O backend e o catalogo permanecem a autoridade final. Caminhos deterministicos atendem fatos catalogados; a LLM trata linguagem residual e nunca libera busca sem gates e proveniencia.

## Prioridade 1 - Integracao Do Fluxo HTTP De Conversacao Com A Convert

- [x] Categoria 1A - Recuperar a mesma solicitacao apos timeout sem duplicar o processamento.
  - Usar temporariamente uma chave derivada de `source`, `room_id`/`conversation_id`, filial e texto normalizado da mensagem. Guardar no Redis o estado `processing` e, ao concluir, a resposta completa, incluindo `actions`, `handoff`, `confidence` e identificadores de rastreamento.
  - Iniciar o trabalho uma unica vez e garantir que ele continue no servidor mesmo se a conexao HTTP original for encerrada pela Convert. Persistir o estado para que uma reinicializacao do processo nao deixe a chave eternamente presa como `processing`; definir expiracao e recuperacao de falhas.
  - Reter a resposta concluida por 5 minutos. Uma repeticao da mesma solicitacao durante esse prazo deve devolver a resposta armazenada imediatamente, sem chamar novamente o `docker-agent` nem atualizar o historico/estado da conversa outra vez.
  - Se a solicitacao ainda estiver em andamento quando o fluxo repetir o POST, aguardar no servidor por no maximo 35 segundos. Se continuar pendente, devolver um resultado explicito `processing`, dentro do limite de 40 segundos da Convert. Se concluir durante a espera, devolver o resultado final.
  - Manter o identificador e o texto identicos em todas as repeticoes do mesmo ciclo. Registrar `trace_id`, estado, duracao e numero de tentativas para diagnosticar o ciclo sem depender dos logs da Convert.
- [ ] Categoria 1B - Diferenciar o proximo passo conversacional pelo campo `stage` e rotear o fluxo da Convert.
  - Incluir no retorno final um campo `stage` estavel, mapeado na Convert para uma variavel como `$estado_ia`, e usar um bloco `Validar Condicoes` para rotear o fluxo.
  - Valores de etapa: `more_info` para enviar uma pergunta e aguardar a resposta do cliente; `mostrar_produtos` para seguir para apresentacao dos itens; `transfer_to_human` para encaminhar ao canal humano. Definir tambem um valor de contingencia para respostas concluidas sem essas acoes.
  - Definir precedencia deterministica: `transfer_to_human` quando `handoff.required=true`; `more_info` quando houver acao `request_info`, inclusive quando a resposta tambem trouxer candidatos para escolha; caso contrario `mostrar_produtos` quando houver `show_items`.
  - Manter `status` do processamento separado de `stage` conversacional: `processing`/`completed` controlam espera e repeticao; `stage` so e avaliado depois de `completed`. A Convert deve rotear `processing` para aguardar e repetir antes de enviar `$resposta_ia`; apos a conclusao, enviar a resposta e seguir o caminho indicado por `$estado_ia`.
  - Mapear tambem os dados de `actions`/itens necessarios para a etapa de apresentacao de produtos. No caminho de handoff, nao iniciar outra rodada automatica de perguntas.
- [ ] Categoria 1C - Validar a implementacao de ponta a ponta.
  - Cobrir com regressao chamadas repetidas concorrentes, repeticao enquanto processa, recuperacao de resultado concluido, expiracao dos 5 minutos, falha/timeout do agente, reinicio durante processamento, atualizacao unica do historico, resposta com handoff e mensagens diferentes na mesma conversa.
  - Validar manualmente na Convert o caminho completo: resposta abaixo de 40 segundos; timeout inicial seguido de resultado pronto; repeticao ainda em `processing`; entrega final; cada valor de `stage`; handoff; e limite de tentativas/expiracao.

**Limitacao aceita nesta primeira versao:** sem um identificador unico fornecido pela Convert para cada mensagem, duas mensagens iguais na mesma conversa e filial dentro da janela de retencao podem compartilhar a chave e ser confundidas. A normalizacao e a janela de 5 minutos reduzem o risco, mas nao o eliminam. Reavaliar quando for possivel enviar um ID estavel da mensagem.

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
  - salvar adapter, checkpoints e manifest fora da GPU; comparar baseline/candidato; validar Ollama sem substituir o ativo; promover apenas com criterios aprovados e rollback documentado.

## Prioridade 4 - WhatsApp

- [ ] Criar e proteger `POST /webhooks/whatsapp` no `docker-comm`.
- [ ] Mapear telefone para origem, conversa persistente e filial.
- [ ] Enviar pela API oficial da Meta, controlando duplicatas e reentregas.
- [ ] Usar dominio estavel da VPS via Nginx e testar handoff, follow-up, multi-item e indisponibilidade sem expor servicos internos.



## Prioridade 5 - Recuperacao Semantica E Operacao

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
