# TODO - Proximas Entregas Do Produto (docker-agent)

Este arquivo contem somente trabalho pendente. Entregas concluidas, evidencias e decisoes ficam em [HISTORICO.md](HISTORICO.md), [PROGRESS.md](PROGRESS.md) e [DECISIONS.md](DECISIONS.md).

Revisado em 22/09/2026. A ordem abaixo prioriza operacao segura, conversa, avaliacao comercial, fine-tuning e integracoes.

## Ordem De Execucao

1. Proteger e estabilizar a VPS.
2. Fechar os fluxos conversacionais que bloqueiam a seguranca do fluxo.
3. Preparar e executar fine-tuning controlado em GPU.
4. Integrar WhatsApp apos a beta estavel.
5. Retomar a avaliacao comercial e a divida deterministica registrada na Prioridade 4.5.
6. Avaliar recuperacao semantica e otimizacoes com dados reais.

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
  - salvar adapter, checkpoints e manifest fora da GPU; comparar baseline/candidato; validar Ollama sem substituir o ativo; promover apenas com criterios aprovados e rollback documentado.

## Prioridade 4 - WhatsApp

- [ ] Criar e proteger `POST /webhooks/whatsapp` no `docker-comm`.
- [ ] Mapear telefone para origem, conversa persistente e filial.
- [ ] Enviar pela API oficial da Meta, controlando duplicatas e reentregas.
- [ ] Usar dominio estavel da VPS via Nginx e testar handoff, follow-up, multi-item e indisponibilidade sem expor servicos internos.


## Prioridade 4.5 - Avaliacao Comercial E Divida Deterministica Pos-Fine-Tuning

- [ ] Validar manualmente todos os tipos de peca contra o ERP antes de iniciar a rodada de correcoes
  - variar modelos e anos de veiculos; registrar consulta, aplicacao, conversa,
    codigos do ERP e codigos da IA em
    `docs/assets/datasets/erp_manual_type_validation_v1.json`;
  - comparar itens ausentes, extras e resultados vazios; fechar cada tipo com
    validacao humana antes de alterar regra ou ranking;
  - caso inicial `batentes_suspensao_s10_1996_dianteiro_001`: a conversa e a
    aplicacao funcionam, mas o ERP mostrou nove codigos e a IA retornou cinco;
    revisar os quatro codigos ausentes antes de fechar a cobertura do tipo.
  - caso `atuador_embreagem_ecosport_2008_001`: a IA perguntou lado e nao
    retornou itens; confirmar no ERP quais dos oito candidatos sao aplicaveis a
    EcoSport 2008 e se atuadores de embreagem diferenciam lado.
  - caso `bieleta_ecosport_sem_ano_timeout_e_retentativa_001`: a conversa refeita
    sem ano perguntou ano e lado e retornou cinco candidatos; validar aplicacao
    dos oito codigos ERP. A primeira tentativa expirou e fica registrada como
    incidente transitorio de timeout, separado da avaliacao de cobertura.
- [ ] Depois de validar todos os tipos, consolidar os erros recorrentes e corrigi-los no catalogo, extractor ou SQL; adicionar cada causa confirmada como regressao.
- [ ] Reexecutar a bateria real no ERP quente com rotulos humanos
  - medir top-1, top-3, candidatos incompativeis, empates e `no_match`; transformar correcoes em regressao sem regras por frase.
  - comparar `application_corroboration_v1` com o baseline no mesmo conjunto;
    os bonus de corroboracao sao heuristicas iniciais, ainda sem calibracao retida.
- [ ] Revisar divergencias entre titulo e aplicacao cadastrada no ERP
  - `YM6160` informa 1998/2002 no titulo, mas tem aplicacoes Corolla 2002/2008;
    corrigir a origem com avaliador humano, sem usar reranking como correcao do cadastro.
- [ ] Calibrar `confidence` e `score` depois da avaliacao rotulada
  - manter `confidence` como heuristica de fluxo e `score` como relevancia ate haver dados para calibracao.
- [ ] Integrar estoque e preco por filial antes de respostas comerciais
  - `branch_id` ainda nao filtra o SQL; confirmar explicitamente ate a integracao.

- [ ] Retomar os casos determinísticos observados na bateria de 22/09
  - reproduzir `real_004` no commit que for avaliado antes de alterar a regra:
    o relatorio encontrou retorno para `polia bomba de agua` apos `2013`,
    embora a regressao local cubra a troca para rolamentos;
  - normalizar `quadro de suspensao` de `real_043` sem deixar a busca nascer
    como `amortecedores suspensao`;
  - tratar o conflito comercial `com/sem atuador` de `real_045_t2` e separar
    carburador de base/flange em `real_080_t3`;
  - revisar `reason_fields` dos falsos `no_match` de `real_032` e `real_028`;
    classificar empates como aceitaveis ou problemáticos antes de alterar pesos.

Esses itens foram adiados para nao misturar defeitos de catalogo, entidade,
estado e atributo comercial com o experimento de fine-tuning. Eles nao entram
como alvo de treinamento nem como evidência de ganho do adapter; permanecem
regressoes congeladas para a comparacao posterior.


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
