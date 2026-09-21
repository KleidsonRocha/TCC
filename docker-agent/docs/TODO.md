# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 21/09/2026. A ordem abaixo prioriza operacao segura, conversa, avaliacao comercial, fine-tuning e integracoes.

## Ordem De Execucao

1. Proteger e estabilizar a VPS.
2. Fechar os fluxos conversacionais restantes.
3. Medir e corrigir ranking com rotulos humanos no ERP quente.
4. Preparar e executar fine-tuning controlado em GPU.
5. Integrar WhatsApp apos a beta estavel.
6. Avaliar recuperacao semantica e otimizacoes com dados reais.

O backend e o catalogo permanecem a autoridade final. Caminhos deterministicos atendem fatos catalogados; a LLM trata linguagem residual e nunca libera busca sem gates e proveniencia.

## Prioridade 0 - Seguranca, Operacao E Beta

- [ ] Exigir protecao administrativa antes da exposicao externa
  - configurar `REVIEW_API_KEY` ou autenticacao equivalente;
  - impedir acesso aberto a `/review/*`; limitar texto, historico, itens e candidatos; restringir `/respond` ao gateway autorizado quando receber estado do chamador.
- [ ] Separar saude do processo e prontidao das dependencias
  - manter `/health` leve; expor prontidao degradada de catalogo, ERP e inferencia, com timeouts documentados.
- [ ] Endurecer a exposicao de portas da stack
  - publicar somente proxy reverso; restringir Redis, PostgreSQL, Ollama e APIs internas; conferir firewall e origem da conexao de saida ao ERP.
- [ ] Automatizar backup e restore de PostgreSQL e Redis
  - cobrir catalogo, regras, fila de revisao, dataset e estados conversacionais necessarios para recuperacao.
- [ ] Fechar beta na VPS com evidencias do canal real
  - repetir conversas por API e `docker-comm`, com Redis; revisar amostra curada de aplicacoes/produtos; registrar que HTTP verde nao prova encaixe comercial.

## Prioridade 1 - Fluxos Conversacionais Restantes

- [ ] Dar continuidade util quando o cliente responder `nao sei`
  - usar outro discriminador com evidencia ou oferecer atendimento humano; limitar repeticoes; cobrir `radiador Gol 2010 -> nao sei a motorizacao`.
- [ ] Corrigir cobertura lexical de pecas e marcas comerciais
  - reconhecer `4 velas NGK para Gol 2010 1.0`, preservando familia, quantidade e marca; governar aliases no catalogo e manter `preferred_product_brand` separado da marca do veiculo.
- [ ] Confirmar familia em descricoes funcionais e sintomas
  - nao fixar familia sem evidencia; perguntar com candidatos controlados ou fazer handoff.
- [ ] Tratar pedido de vendedor e sintomas com motivo correto
  - encaminhar pedido explicito sem inferencia desnecessaria; preservar dados do veiculo e nao tratar sintoma como familia inexistente.

## Prioridade 2 - Ranking E Avaliacao Comercial

- [ ] Instrumentar a busca com candidatos brutos, rejeitados, filtrados e ranqueados, seus motivos e `score_breakdown`.
- [ ] Refinar desempates e pesos do ERP
  - reduzir empates e priorizar aplicacao exata; revisar complemento, injecao, motor, transmissao e atributos comerciais somente com evidencia medida.
- [ ] Reexecutar a bateria real no ERP quente com rotulos humanos
  - medir top-1, top-3, candidatos incompativeis, empates e `no_match`; transformar correcoes em regressao sem regras por frase.
- [ ] Calibrar `confidence` e `score` depois da avaliacao rotulada
  - manter `confidence` como heuristica de fluxo e `score` como relevancia ate haver dados para calibracao.
- [ ] Integrar estoque e preco por filial antes de respostas comerciais
  - `branch_id` ainda nao filtra o SQL; confirmar explicitamente ate a integracao.

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

- [ ] Avaliar classificador auxiliar em portugues somente se regras e embeddings deixarem lacuna mensuravel.
- [ ] Avaliar `pgvector` somente depois da prova semantica em memoria.
