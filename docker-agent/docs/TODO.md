# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 01/10/2026. A ordem abaixo prioriza operacao segura, conversa, avaliacao comercial, fine-tuning e integracoes.

## Ordem De Execucao

1. Fechar a integracao do fluxo HTTP de conversacao com a Convert: roteamento por etapa e validacao ponta a ponta.
2. Preparar e executar fine-tuning controlado em GPU.
3. Integrar WhatsApp apos a beta estavel.
4. Retomar a avaliacao comercial e a divida deterministica registrada na Prioridade 4.5.
5. Avaliar recuperacao semantica e otimizacoes com dados reais.

O backend e o catalogo permanecem a autoridade final. Caminhos deterministicos atendem fatos catalogados; a LLM trata linguagem residual e nunca libera busca sem gates e proveniencia.

## Prioridade 1 - Integracao Do Fluxo HTTP De Conversacao Com A Convert

- [ ] Categoria 1B - Concluir o roteamento por `stage` no fluxo publicado da Convert.
  - Mapear `$.stage` para `$estado_ia` e validar cada saida do bloco `Validar Condicoes`: `more_info`, `mostrar_produtos`, `transfer_to_human` e `fallback`.
  - Rotear `processing` para aguardar e consultar novamente antes de enviar `$resposta_ia`; somente apos `completed`, enviar a resposta e avaliar `$estado_ia`.
  - Apresentar `$itens_ia` quando houver produtos. No handoff, impedir outra rodada automatica de perguntas e confirmar a transferencia para atendimento humano.
- [ ] Categoria 1C - Validar a implementacao de ponta a ponta.
  - Cobrir com regressao chamadas repetidas concorrentes, repeticao enquanto processa, recuperacao de resultado concluido, expiracao dos 5 minutos, falha/timeout do agente, reinicio durante processamento, atualizacao unica do historico, resposta com handoff e mensagens diferentes na mesma conversa.
  - Validar manualmente na Convert o caminho completo: resposta abaixo de 40 segundos; timeout inicial seguido de resultado pronto; repeticao ainda em `processing`; entrega final; cada valor de `stage`; handoff; e limite de tentativas/expiracao.

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

- [ ] Filtrar as opcoes sugeridas de motorizacao pelo ano informado.
  - No reteste da EcoSport 2008 em 01/10/2026, a pergunta ofereceu `DRAGON` e `SIGMA`; o CSV versionado so registra `DRAGON` a partir de 2017 e `SIGMA` a partir de 2012 para esse modelo.
  - A aceitacao da resposta ja considera os intervalos, mas `_engine_options_for_model` apresenta todas as opcoes do modelo. Aplicar o mesmo criterio de ano a exibicao e cobrir a pergunta e a resposta com regressao.
- [ ] Investigar falso negativo da busca de bieleta para S10 2009, lado direito, na filial 1.
  - Fallback condicional de lado/posicao implementado e testado localmente em 02/10/2026. Atualizar o `docker-agent` na VPS e repetir o pedido no Omni; conferir `directional_fallback`, codigos recuperados e a confirmacao da direcao na resposta. O filtro de acessorios continua ativo.
  - No teste da Convert em 01/10/2026, a API pesquisou `part_query="bieletas"`, `vehicle_model="S10"`, `vehicle_year=2009` e `side="right"`, mas respondeu que nao encontrou itens.
  - A consulta manual do ERP por `BIELETA S10 2009` exibiu os codigos `531.2124`, `031.0737` e `031.1199`; a descricao de `531.2124` menciona dianteira `LD/LE` e S-10 1997/2011. Confirmar a aplicacao cadastrada antes de concluir compatibilidade.
  - Comparar os dados de `soccol.item_search_candidates` e `soccol.item_search_applications` com a tela do ERP; identificar se a divergencia vem da extracao, da normalizacao `S10`/`S-10`, do filtro de lado, da aplicacao/ano, da filial ou do snapshot. Registrar o motivo de rejeicao e criar regressao para a causa confirmada.
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
