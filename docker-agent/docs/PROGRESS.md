# Progresso Do Projeto

## Material Local Movido Para Tmp Em 19/10/2026

- A pedido do usuario, a pasta `Documents/` da raiz foi movida integralmente
  para `.tmp/Documents/`, tambem na raiz. PDF, diagrama, relatorios, ZIPs e
  evidencias locais preservados; os dois arquivos academicos restantes foram
  retirados do versionamento. Conteudo fora do Git, sem reescrever seu historico.
- README, AGENTS e localizacao do relatorio ajustados. A documentacao vigente
  em `docker-agent/docs/` e os artefatos congelados em `fine_tuning_gpu/`
  permanecem nos seus locais.

## Relatorio Comparativo Do Experimento LoRA Em 19/10/2026

- Produzido relatorio em HTML e Markdown com parametros efetivos, splits,
  metodologia pareada, resultados, limites, caminhos dos testes e reproducao.
  Entrega local em `.tmp/Documents/relatorio_comparativo_qwen_20261019/` na raiz e ZIP
  correspondente, ignorados pelo Git para preservar a limpeza do repositorio.
- Conferidos os 796 JSONs individuais, classificacoes, contagens de turnos,
  medias de categoria, aprovacoes golden, hashes das entradas e do adapter.
  Pacote inclui conversas, buscas, chamadas e tempos, sem duplicar pesos,
  checkpoints ou dump de banco. Evidencias congeladas originais intactas.
- Esta entrega consolida o experimento existente, sem nova inferencia ou treino;
  as correcoes posteriores do backend/canal nao sao ganhos atribuidos ao adapter.

## Complemento Do Reteste No Canal Em 19/10/2026

- Usuario confirmou a implantacao da VPS no commit 2095596, com catalogo
  aplicado e health/ready aprovados; Clio retornou SK-813 no Omni/Convert.
  Isso nao encerra o aceite: S10/Gol com `semieixo` tiveram handoff incorreto
  e FH 460 2016 recebeu sugestao `D13K460`, recusada ao responder.
- [x] Mapear `semieixo`/`semieixos` para `semi eixo`, sem ampliar scopes nem
  substituir a identidade explicita `semieixo diferencial`. Curadoria agora
  possui 45 decisoes. Mensagens naturais exatas adicionadas a bateria.
- [x] Filtrar sugestoes de motor pelos intervalos do modelo/ano, como na
  aceitacao do follow-up. D13K460, registrado desde 2023, nao e sugerido para
  FH 460 2016. Sem intervalo compativel, nao reintroduzir opcoes de outros anos.
  Cobertos anos limite, intervalos repetidos/abertos, ausencia de ano e EcoSport.
- Confirmado no catalogo local real com atualizador em transacao revertida:
  S10/Gol passam a pedir versao sem LLM, preservando veiculo e ABS negativo;
  FH 460 2016 oferece somente D 13 C 460. Bateria: 170 cenarios/208 turnos.
  Evidencias em `.tmp/eval/channel_alias_engine_results_20261019.json` e
  `.tmp/eval/channel_alias_engine_20261019.xml`.
- Regressao final: **604 testes aprovados, nenhum ignorado**, incluindo SQL
  no PostgreSQL local e reproducibilidade da bateria. Uma advertencia de
  depreciacao Starlette/AnyIO permanece. Verificacao de diff sem erros.
- [x] Reteste do complemento no Omni/Convert observado nos prints enviados
  pelo usuario em 19/10/2026, entre 15:35 e 15:37:
  - S10 2017 2.5: reconheceu `semieixo`, pediu versao, aceitou
    `LTZ 2.5 FLEX 4X4 CD AT` e apresentou KJH0309.
  - Gol 2003 1.0 sem ABS: reconheceu a familia, pediu versao e, apos
    `nao sei`, encaminhou ao humano sem repetir a pergunta.
  - FH 460 2016: sugeriu somente `D 13 C 460`, aceitou a resposta e
    concluiu em `no_match`, sem apresentar a presilha incorreta.
  Evidencia visual do canal; hash do novo deploy, trace_ids e estado interno
  nao foram enviados neste reteste. O print do Gol nao audita o filtro ABS
  interno; sua preservacao permanece coberta pelos testes locais.
- Aceite parcial confirmado nesses tres fluxos. O `no_match` da caixa de
  bateria nao comprova indisponibilidade geral ou compatibilidade comercial.
  Palio/ELX RST III e contradicoes no canal continuam no TODO.

## Limpeza Inicial Do Repositorio Em 19/10/2026

- Retirados do versionamento dois relatos antigos de marco em `Documents/`
  e os rascunhos `estrutura.md`/`esqueleto.md` do gateway, com copias locais
  preservadas. Guias atuais, decisoes e historico consolidado continuam como
  referencias; README e AGENTS ajustados.
- Ignore da raiz protege temporarios, caches e os documentos substituidos.
  Codigo, testes, datasets, snapshot LFS e material academico preservados.
  Limpeza documental, sem alteracao de runtime, banco ou reescrita do historico Git.

## Curadoria E Refinamentos No Docker Local Em 19/10/2026

- [x] Curar identidades, aliases, composicao e requisitos por familia.
  - Revisados os 21 aliases conflitantes: 43 decisoes e 19 conceitos versionados;
    15 formas vagas pedem esclarecimento. Scopes curados para eletroventilador,
    trizeta e kits, com identidade completa e bloqueio de acessorios preservado.
    Auditoria somente leitura dos 86 handoffs por lado/eixo; removida exigencia
    padrao apenas de quatro familias, mantendo filtros explicitamente pedidos.
    Sete criterios historicos afetados nao representam sete casos recuperados.
- [x] Separar versao, combustivel, transmissao e ABS; normalizar abreviacoes
  e negacoes sem confundir lado, posicao e eixo. Combustivel nao pode vir de
  outro motor da mesma lista. Estado Redis conserva ABS falso e item ativo.
  Ranking sem novos pesos; LLM nao pode inventar refinamentos.
- [x] Construir e implantar agente/gateway no Docker local, sem recriar volumes.
  - PostgreSQL, Redis e Ollama preservados. Backup de catalogo, rootfs anterior
    e imagens de rollback salvos antes da aplicacao transacional.
    VPS e Omni/Convert externo ficam pendentes, conforme escopo autorizado.
- Suite final: **593 testes do agente e 33 do gateway aprovados, nenhum
  ignorado**, incluindo controles SQL e Redis. Uma advertencia de depreciacao
  Starlette/AnyIO no agente. Bateria versionada: 168 cenarios/206 turnos;
  experimento LoRA e resultados historicos preservados.
- O primeiro reteste HTTP passou nas assertions estruturais, mas a inspecao
  encontrou uma presilha classificada como caixa de bateria no FH 460.
  Adicionado padrao de identidade e regressao negativa. A prova de motor/versao
  agora consulta a opcao veicular independentemente da disponibilidade da peca;
  a busca final continua exigindo identidade e aplicacao completas.
- Reteste final no ERP ativo/Ollama local: **17 cenarios e 20 turnos por
  caminho (agente e gateway), 40 turnos aprovados**, com health/ready HTTP 200
  e estado/historico recuperados do Redis. Clio retornou SK-813; S10 preservou
  a versao integral e retornou KJH0309. FH 460 preservou o motor integral e
  retornou `no_match`, sem apresentar a presilha R-3408. Os titulos adversariais
  de polia/rolamento ainda usaram LLM e levaram aproximadamente 56-120 segundos
  neste Ollama em CPU; o reteste nao comprova melhoria de latencia.
- Evidencias, backups, XMLs e conversas em
  [family_refinements_20261019](../.tmp/eval/family_refinements_20261019).
  [Reteste final](../.tmp/eval/family_refinements_20261019/live_http_retest.json),
  [reteste inicial preservado](../.tmp/eval/family_refinements_20261019/live_http_retest_initial.json)
  e [manifesto](../.tmp/eval/family_refinements_20261019/deployment_manifest.json).
  Decisao em [DECISIONS.md](DECISIONS.md#48-curadoria-de-familias-e-refinamentos-tipados).
  A bateria revisada dos 371 casos e a validacao comercial continuam pendentes.

## Identidade E Follow-Up Concluidos Localmente Em 19/10/2026

- [x] Preservar componente e aplicacao explicitamente solicitados antes de liberar busca.
  - Composicoes polia/bomba, tapa-po/cilindro e rolamento/amortecedor mantidas
    como uma identidade; aplicacao apos `para` prevalece sobre modelos/anos
    do titulo. Regressoes Clio, Palio, S10, correcao, negacao e multiplos itens.
    Direcoes contraditorias pedem confirmacao antes de LLM/busca; componente
    composto sem mapeamento pede esclarecimento, sem virar a peca interna.
- [x] Governar respostas de follow-up e impedir perda de dados ja informados.
  - `pending_slot` governa versao/motor textual; `4X4` e `460` na resposta nao
    substituem o modelo. Catalogo contextual ou prova na mesma aplicacao
    aceitam `ELX RST III`, `LTZ 2.5 FLEX 4X4 CD AT` e o motor completo
    `12.8 L 24V SOHC L6 D 13 C 460`. Estado/historico e item ativo preservados;
    resposta desconhecida pergunta, fonte indisponivel encaminha.
- Verificacao final: **546 testes aprovados, nenhum ignorado**, incluindo
  os 104 controles SQL, com XML em
  [pytest.xml](../.tmp/eval/request_identity_follow_up_20261019/pytest.xml).
  Build Linux concluido. O snapshot recusou corretamente criacao de tabelas;
  os controles SQL usaram tabelas temporarias/rollback no PostgreSQL local.
  Uma advertencia de depreciacao do Starlette/AnyIO permanece.
- No snapshot congelado, cinco cenarios HTTP/oito turnos passaram sem LLM,
  incluindo os tres follow-ups reais; tres sondas adicionais confirmaram a
  extracao dos titulos polia/rolamento/Clio. Requisicoes, respostas, criterios,
  itens, diagnosticos e tempos em
  [results.json](../.tmp/eval/request_identity_follow_up_20261019/results.json).
  Sao controles estruturais; o item de referencia da caixa de bateria, por
  exemplo, ainda exige curadoria comercial de identidade.
- Bateria versionada ampliada de 151 para 159 cenarios/197 turnos, com oito
  casos novos; expectativas estruturais nao promovidas a rotulos comerciais
  ou treino. Decisao em [DECISIONS.md](DECISIONS.md#47-preservar-identidade-e-governar-follow-up-pelo-contexto).
  Implantacao/canal, scopes de kits/aliases e reexecucao revisada dos 371
  permanecem no [TODO.md](TODO.md). O experimento original esta preservado.

## Auditoria Tecnica Dos 371 Casos Do Modelo Base Em 19/10/2026

- Cruzados os 371 registros do original BF16 com o snapshot e o ERP real em
  transacao `repeatable read`, somente leitura. O ERP atual e o snapshot da
  comparacao registram 52.798 itens/1.779.443 aplicacoes; a contagem de
  1.776.907 pertence ao manifesto de bootstrap de 14/09/2026. Na amostra de
  623 codigos/53.874 aplicacoes, os campos atuais coincidem com o snapshot.
- Preparadas fichas de todos os casos e identificadas causas de extracao,
  contexto/follow-up, aliases/scopes, requisitos e referencias questionaveis.
  Foram 351 consultas de diagnostico por codigo em 39 buscas de 38 casos
  suspeitos no banco isolado, nove sondas de extracao sem IA e cinco consultas
  dirigidas adicionais. Algumas retiram restricoes apenas para explicar o
  bloqueio; nao representam correcao aprovada nem ganho de cobertura medido.
- A extracao congelada reproduziu troca de polia por bomba, rolamento por
  amortecedor, modelo 4X4 em resposta de versao e falha em motor 12.8/textual.
  Dos 61 nao concluidos, 60 nao executaram busca e 33 repetiram pergunta;
  os 105 handoffs por desconhecimento nao chamaram LLM, sendo 86 por lado/eixo.
  Ha 21 aliases com mais de uma familia canonica. A revisao comercial segue
  pendente; os 34 suspeitos nao foram convertidos em falsos negativos confirmados.
- Relatorio e plano em
  [analysis.md](../.tmp/eval/base_categories_review_20261019/analysis.md),
  fichas filtraveis em
  [review.html](../.tmp/eval/base_categories_review_20261019/review.html) e
  registros completos em
  [cases_review.json](../.tmp/eval/base_categories_review_20261019/cases_review.json).
  Lotes de correcao no [TODO.md](TODO.md). Esta etapa produziu auditoria e
  planejamento; nenhuma correcao de runtime ou escrita no ERP foi aplicada.

## Experimento LoRA Concluido E Nova Adaptacao Adiada Em 19/10/2026

- Treinamento LoRA em BF16 e comparacao original/adapter executados, com
  artefatos preservados localmente. A execucao nao usou QLoRA 4-bit.
  Resultados e limites consolidados em
  [HISTORICO.md](HISTORICO.md#experimento-lora-em-gpu-de-19102026).
- O adapter nao apresentou ganho global na configuracao avaliada; o modelo
  ativo foi mantido. Nova adaptacao, publicacao/validacao do adapter no
  Ollama e infraestrutura de GPU com fallback foram adiadas por orientacao
  do usuario. Auditoria de mascara/truncamento, benchmark independente e
  paridade de contratos continuam requisitos para eventual retomada.
- A ordem vigente passa a priorizar avaliacao comercial e correcoes
  deterministicas em [TODO.md](TODO.md). A decisao de 19/10/2026 substitui
  indicacoes anteriores deste documento de que preparar fine-tuning seria
  o proximo bloco. O detalhamento da preservacao consta ao final desta pagina.

## Auditoria Conversacional Por Categoria Retomada Em 19/10/2026

- Implementado `scripts/eval/evaluate_category_search.py`: uma conversa por
  categoria/subcategoria, com historico/estado e respostas incrementais baseadas
  em referencia real. Usa o fluxo interno do checkout em processo isolado,
  fonte ERP somente leitura e captura para treinamento desabilitada.
- Preparados 371 casos: 361 do catalogo ativo (23 categorias/338 subcategorias)
  e dez complementares (grupo ERP 24 e nove subgrupos ausentes do catalogo).
  A consulta inicial encontrou 335 produtos nessas nove entradas.
- Checkpoint revisado de 350 conversas: 130 com itens estruturalmente coerentes,
  36 suspeitas de falso negativo, quatro suspeitas de item inadequado, 104
  encaminhamentos por dado desconhecido, 33 entradas sem itens na fonte,
  42 sem produtos apresentados apesar do cadastro e uma falha operacional.
  Trinta confirmacoes de item unico no texto foram recuperadas e conferidas
  na fonte. Tres falhas anteriores de busca passaram na repeticao.
- A bateria ainda estava em execucao neste registro. O consolidator com
  `--watch` salva uma versao parcial revisada e a substitui automaticamente
  pelo resultado completo quando todos os casos terminarem. Os processos
  precisam permanecer ativos com Docker ligado. Estado e contagem definitivos
  ficam em `.tmp/eval/category_audit_20261019/report.json`; HTML filtravel,
  perguntas e observacoes ficam no mesmo diretorio.
- Doze testes do avaliador/consolidator aprovados, incluindo confirmacao textual,
  preservacao de dialogos, filtros divergentes e substituicao parcial/completa.
  Nao houve implantacao nem teste de transporte pelo gateway/WhatsApp.
- Uma conversa por entrada nao mede recuperacao de todo o estoque. Coerencia
  de cadastro nao certifica encaixe; kits/acessorios e classificacoes divergentes
  precisam de revisao humana. Referencias foram congeladas, mas o ERP permaneceu
  vivo entre as retomadas; esta bateria nao e um benchmark de carga controlado.

## Busca Geral Por Viscosidade De Oleo Corrigida Localmente Em 14/10/2026

- `variant` no formato de viscosidade e familia `lubrificantes` passa a
  filtrar nome/titulo do produto, sem exigir essa versao na aplicacao veicular.
  Payload, schema, views e dataset de treino permanecem com o mesmo contrato.
- `5W40`, `5W-40` e `5 W 40` sao aceitos; limites de palavra separam graus
  diferentes e familia continua obrigatoria. Demais filtros e codigos exatos
  sao preservados. Golden SQL inclui sete novos casos e contraexemplos.
- Validacao em container com os arquivos locais: 239 testes aprovados e
  104/104 verificacoes SQL no contrato e no COPY/snapshot. Consulta somente de
  leitura ao catalogo local retornou sete itens para `quero o oleo 5w40`,
  incluindo `TEX-3117`; busca por codigo, com e sem viscosidade, retornou
  somente esse item. Relatorio em `.tmp/eval/oil_viscosity_golden.json`.
- Rebuild do agente em execucao e implantacao/reteste no Omni/Convert da VPS
  continuam pendentes. Os testes nao alteraram o modelo ativo nem os dados ERP.

## Fallback De Lado E Posicao Implementado Localmente Em 02/10/2026

- Consulta com `side` ou `position` que retorna zero produtos repete uma vez
  sem ambos. Familia/codigo, acessorios, aplicacao veicular, eixo e marca
  preferida permanecem iguais. Erro continua sendo indisponibilidade.
- Criterios originais permanecem no estado. Diagnosticos guardam tentativa
  estrita, campos retirados e resultado ampliado; a resposta pede confirmacao
  da direcao, inclusive quando a lista tem somente um candidato.
- Desambiguacao pode perguntar por lado/posicao retirados, quando separarem
  os candidatos. Nenhuma chamada adicional de LLM ou migracao de banco.
- Validacao local: 103 testes focados aprovados e 90/90 verificacoes SQL
  golden aprovadas no PostgreSQL. O teste de estrutura do golden set tem
  falha preexistente: tres casos de ranking sem `message` (fora desta mudanca).
- Atualizacao do `docker-agent` e reteste dos tres codigos de bieleta no Omni
  da VPS permanecem pendentes. O fallback nao altera `accessory_identity` e
  nao garante recuperar um item rejeitado por essa regra ou pela aplicacao.

Estado em 02/10/2026. Historico de problemas, benchmarks e relatorios em
[HISTORICO.md](HISTORICO.md); pendencias e criterios de aceite em
[TODO.md](TODO.md). As Categorias 1B e 1C da integracao com a Convert foram
encerradas por confirmacao do usuario em 02/10. A avaliacao comercial permanece
separada e pendente.

## Estado Atual

- A Prioridade 4 de integracao com WhatsApp foi encerrada em 02/10 por
  confirmacao do usuario: o sistema interno Omni/Convert faz a conexao com o
  canal e integra o atendimento ao TCC. A entrega adotou esse intermediario;
  webhook proprio e cliente direto da Meta deixam de ser requisitos do escopo.
  Responsabilidades e aceite registrados em [DECISIONS.md](DECISIONS.md) e
  [HISTORICO.md](HISTORICO.md).
- A recuperacao de turno por `trace_id` foi implantada no `docker-comm`.
  O usuario confirmou em 02/10 a conclusao do roteamento por `stage` (1B) e
  da validacao ponta a ponta (1C) na VPS/Convert, incluindo os cenarios
  controlados anteriormente testados. Escopo e origem da confirmacao em
  [HISTORICO.md](HISTORICO.md); contrato mantido em [DECISIONS.md](DECISIONS.md).
- O catalogo da VPS foi recriado em 01/10 apos detectar anos invalidos em
  todos os registros de motor. O banco novo tem 10.834 motores e zero anos
  invalidos; a resposta `ZETEC ROCAM` para EcoSport 2008 avancou para a busca
  e retornou tres candidatos no canal Navi. Filtrar as opcoes sugeridas pelo
  ano continua pendente.
- Reranking `application_corroboration_v1` aplicado no SQL real e no snapshot,
  antes do limite; aliases de versao preservam JOY e SURF. Diagnosticos internos
  identificam backend, criterios, evidencia e componentes do score.
- Validacao local: 233 testes focados e 90/90 verificacoes golden aprovados;
  replay de tres consultas produziu a mesma ordem no ERP quente e no snapshot.
  Avaliacao comercial completa e calibracao continuam pendentes.
- A latencia residual de `real_041` foi corrigida: os follow-ups direcionais
  nao chamam a LLM depois de uma busca concluida. A reproducao completa 3/3
  terminou entre 1,10 s e 1,57 s; a bateria longa continua pendente.
- O relatorio consolidado de 22/09 registrou casos restantes de entidade,
  estado, atributo comercial, acessorio e `no_match`. Eles foram movidos para
  a Prioridade 4.5, fora do treinamento, preservando a bateria atual como
  baseline pre-fine-tuning. A preparacao de QLoRA passa a ser o proximo bloco.

- API `/respond` integra catalogo PostgreSQL, extracao deterministica,
  `deterministic_ask`, `deterministic_bypass` e LLM residual via Ollama.
- Busca e desambiguacao usam candidatos reais e estado conversacional
  persistido pelo `docker-comm` no Redis. Contrato admite `items[]`, com
  correcoes por item ainda pendentes no backlog.
- Revisao humana por conversa/turno, historico de revisoes, promocao e
  exportacao do dataset implementados. Trainer LoRA/QLoRA preparado;
  ainda sem evidencia de run concluida ou de ganho de adapter.

## Negacao, Substituicao E Conflito Antes Da Busca

- O extractor resolve a troca explicita para a parte afirmativa, ignora a
  direcao negada e nao emite clausulas negativas em `items[]`.
- Negacao ou correcao sem substituicao comprovada interrompe a busca com a
  pergunta `intent_resolution`; conflito como `Honda Gol` usa
  `vehicle_identity`.
- O bootstrap passou a aplicar `vehicle_model_brand.csv` diretamente em
  `pre_search_model.brand_id`. Modelos sem mapeamento curado continuam como
  `SEM_MARCA_MAPEADA`, sem inferencia por texto.
- A revisao humana promoveu 1.922 relacoes adicionais, deixando
  `vehicle_model_brand.csv` com 1.971 vinculos. A aplicacao no catalogo local
  atualizou 1.922 registros; a conferencia resultou em 1.971 modelos
  vinculados e 1.523 em `SEM_MARCA_MAPEADA`.
- A auditoria reproduzivel restante em
  `.tmp/catalog/model_brand_review_after_import.csv` possui 5 P1, 43 P2 e
  1.475 P3 pela recorrencia no seed de motores. A fila sera usada para
  promover somente relacoes confirmadas para `vehicle_model_brand.csv`.
- Golden set, bateria estrutural e testes unitarios receberam os quatro casos
  automotivos de regressao. Em 16/09, a suite Docker aprovou 369 testes e o
  golden da LLM aprovou 25/25 casos, incluindo negacao, substituicao e conflito.

## Itens Com Aplicacoes Veiculares Distintas

- A extracao multi-item conserva a identidade completa de cada item e nao
  propaga marca, modelo, ano ou motor de uma clausula para outra.
- Aplicacao comum no fim do pedido continua suportada quando declarada
  explicitamente, por exemplo `radiador e pastilha para Gol 2010 1.0`.
- Foram adicionados casos unitarios e tres cenarios estruturais para veiculos
  distintos, ausencia de contexto e aplicacao comum; todos foram executados
  com sucesso em 16/09.

## Follow-Up De Motor E Listas Comerciais

- O runtime trata motor textual como opcao do catalogo durante uma pergunta
  pendente: `BE`, `Zetec Rocam`, `Duratec`, `Duratec HE`, `Sigma`, `EA111` e
  `EA211` sao validados pelo modelo e, quando existir, pelo intervalo de ano.
- A decomposicao multi-item usa aliases nao sobrepostos do catalogo como
  fronteiras. Quantidade e atributos permanecem no item correspondente;
  aplicacao comum so e herdada sem identidade veicular concorrente.
- As regressões de `real_005`, `real_052`, `real_055`, `real_067` e `real_081`
  foram executadas com `tests/test_rules.py`: 146 aprovados em 17/09. A suite
  completa e a bateria longa continuam pendentes para o fechamento da
  Prioridade 2.

## Contrato Residual E Linguagem Publica

- O payload enviado a LLM residual separa a mensagem atual, seed, estado,
  mensagens anteriores do usuario e contexto do assistant, com precedencia
  declarada. O backend permanece responsavel pela decisao final.
- Perguntas direcionais usam lado esquerdo/direito, posicao dianteiro/traseiro
  e eixo dianteiro/traseiro. A desambiguacao normaliza genero e equivalentes
  em ingles sem confundir eixo com posicao.
- Os testes focados de regras e desambiguacao aprovaram 165 casos em 17/09.

## Correcao De Criterios Durante A Desambiguacao

- Candidatos de desambiguacao agora pertencem aos filtros que os originaram.
  Se o cliente substituir modelo, ano, motor, lado, posicao, eixo, variante,
  marca, marca preferida ou codigo, o runtime elimina a lista pendente e volta
  ao gate de validacao antes de consultar o ERP.
- A correcao `radiador Gol 2010 1.0` para `Corsa 2011 1.4` conserva somente a
  familia omitida na frase de correcao; os atributos do Gol nao sao reutilizados
  como candidatos nem como resultados de busca.
- Foram incluídas regressao unitária, caso no golden set e cenário estrutural
  multi-turno. Os dois turnos foram aprovados em 16/09.

## Identidade E Aplicacao ERP Corrigidas Em 14/09/2026

- Contrato v2: `soccol.item_search_candidates` e `soccol.item_search_applications`.
- Familia validada antes do ranking; radiador nao aceita tampa, kit ou mangueira
  como peca principal. Cinco aliases de tampa/mangueira no CSV e catalogo local.
- Modelo exato (`Gol` != `Golf`); marca, ano, motor e versao coincidem na mesma
  aplicacao. Intervalos separados nao sao unidos; ano desconhecido nao e fim aberto.
- Motores, injecoes e transmissoes pertencem a aplicacao da peca. Somente
  aplicacoes aprovadas fornecem atributos para desambiguacao.
- Nome completo e titulo do proprio item fornecem lado, eixo e posicao.

Evidencias da correcao: 343 testes; 38 casos automotivos de SQL executados
contra integracao e copia do snapshot (76/76). `audit_only_real` aceita somente
`AUD-REAL`, rejeitando `AUD-GOLF`, `AUD-CROSS` e `AUD-CAP`. Golden de pre-search
cobre tampa do radiador e identidade de Golf.

Em 16/09, a consulta online passou a abrir o PostgreSQL do ERP com
`client_encoding=UTF8`, igual ao exportador do snapshot. Isso corrigiu um JSON
em WIN1252 que fazia o driver Python acionar o fallback: a bateria real voltou
a obter quatro radiadores para Gol 2010 1.0 diretamente por `erp_postgres`;
a correcao para Corsa 2011 1.4 tambem consultou o ERP e retornou um item.
Na mesma validacao, a suite completa aprovou 369 testes e o golden residual da
LLM aprovou 25/25 casos. A repeticao na VPS continua necessaria.

Snapshot local: **52.798 itens e 1.776.907 aplicacoes**, exportado do banco
quente em 14/09/2026. Carga validada com rollback e instalada com backup.
API real validada para radiador Gol, tampa, coxim EcoSport e radiador Golf;
resultados e limites em [HISTORICO](HISTORICO.md).

O usuario atualizou o SQL no banco quente. A exportacao somente de leitura
de 14/09, 17:48 UTC, confirmou as duas views: 52.798 itens e 1.779.443
aplicacoes. Essa copia de verificacao ficou em `.tmp/`, preservando o snapshot
versionado anterior. Implantacao e verificacao na VPS continuam no [TODO](TODO.md).

## Follow-ups Deterministicos Corrigidos Em 11/09/2026

Follow-up `2008` preserva ano e contexto do carro; respostas de direcao
respeitam o campo pendente. Coxins exigem posicao, nao eixo; pastilhas nao
exigem motor como campo obrigatorio. Mudancas no catalogo local, CSVs e
regressoes; propagacao na VPS ainda precisa ser confirmada.

## Organizacao De Banco E Documentacao Em 14/09/2026

- `pre_search_init.sql` concentra catalogo, revisao, treino e carga do fallback;
  instalador extrai apenas o bloco de busca para volumes existentes.
- Exportador consulta as views do ERP em transacao somente de leitura,
  com ordem explicita de colunas e UTF-8; dispensa arquivo DDL no checkout.
- Snapshot v2 e manifestos permanecem versionados, com gzip no Git LFS.
- Relatorios antigos e backlog legado consolidados em `HISTORICO.md`;
  novos resultados gerados em `.tmp/eval/`, ignorados pelo Git.
- Testes padrao usam o contrato e COPY; `--integration-sql` permite repetir
  auditoria das relacoes de origem com copia local do SQL externo.

Validacao da reorganizacao: **343 testes aprovados** e **114/114 verificacoes
SQL** (38 casos no contrato, no COPY e nos SELECTs externos fornecidos).
Carga integral pelo instalador consolidado validada com rollback: 52.798
itens e 1.776.907 aplicacoes. Evidencias locais em `.tmp/eval/cleanup_tests.xml`
e `.tmp/eval/cleanup_integration_report.json`.

Bootstrap completo tambem passou em PostgreSQL 16 descartavel, isolado e sem
reutilizar volume: 338 tipos de peca do seed, 52.798 itens, 1.776.907 aplicacoes,
zero aplicacoes orfas e fila de revisao vazia. Os 15 Markdown conferidos nao
tinham links locais quebrados. Smoke do gerador produziu JSON/Markdown em
`.tmp/eval/`. Hashes dos dois arquivos LFS e manifestos conferidos contra o
indice Git: nenhum dos quatro arquivos preparados pelo usuario foi alterado.

## Desambiguacao De Resultados Concluida Localmente

Desambiguacao revisada em 16 e 17/09: atributos incompletos ou com uma opcao
comum a todos os candidatos deixam de gerar perguntas. Ate dez resultados sao
apresentados diretamente; a consulta preserva ate 50 candidatos e pagina o
excedente em grupos de dez. Valores equivalentes sao agrupados; resposta nao
compreendida troca o discriminador ou mostra a lista. Negacao de codigo nunca
seleciona o item negado. Novo filtro explicito fora das opcoes invalida os
candidatos antes de nova validacao e consulta. Os testes focados cobrem
serializacao de `ConversationState`, selecao, negacao, pagina seguinte, troca de
assunto e limite de tentativas no mesmo `ConversationState`.

## Pendencias Principais

Tambem faltam motor textual, avaliacao comercial do ranking, paridade
treino/runtime e validacao da versao atual na VPS. O teste visual confirmou a
nova pergunta de identidade de `coxim`, mas a resposta sugerida `zetec rocam`
ainda nao foi aceita pelo follow-up e repetiu a pergunta de motorizacao.
O [TODO](TODO.md) concentra o trabalho restante; reorganizar arquivos nao
altera a classificacao de prontidao comercial.

## Disponibilidade Do ERP E Concorrencia Da API

- A indisponibilidade da busca deixou de ser tratada como ausencia de produto:
  pedido de uma unica peca recebe HTTP 503; em pedido multiplo, cada peca
  conserva o status `error` e pode ser tentada novamente.
- A resposta, a telemetria e a captura de revisao distinguem `not_found` de
  erro. A captura armazena os resultados por item como uma acao interna,
  sem alterar o contrato HTTP de acoes para o cliente.
- Validacao LLM, busca PostgreSQL e gravacao da fila de revisao sao executadas
  fora do event loop. Ha limite configuravel de duas inferencias e quatro
  buscas simultaneas; LLM usa `LLM_TIMEOUT_MS` e a consulta usa
  `ERP_SEARCH_TIMEOUT_MS`, inclusive como `statement_timeout` no PostgreSQL.
- O auditor da LLM foi isolado por requisicao. Regressao focada confirmou que
  uma inferencia lenta nao bloqueia `/health` nem outra conversa deterministica.

## Operacao Verificada Em 21/09/2026

- A VPS acessa o ERP quente pelo backend `erp_postgres`; conectividade,
  autorizacao e objetos v2 foram conferidos. O snapshot local v2 serve para
  contingencia e reproducao.
- Checklist de deploy e fluxo sem GPU foram verificados. A proxima validacao
  operacional e a beta pelo canal real, com Redis e avaliacao comercial humana.

## Protecao Administrativa E Prontidao Preparadas Em 21/09/2026

- Em producao, a API falha na inicializacao sem `REVIEW_API_KEY` e
  `RESPOND_GATEWAY_API_KEY`. A chave de revisao protege `/review/*`; a chave
  de gateway e exigida quando `/respond` recebe historico ou estado do cliente.
- O `docker-comm` encaminha a chave de gateway em
  `X-Agent-Gateway-Key`. Entradas da API limitam texto, historico, itens e
  candidatos para impedir carga arbitraria do estado conversacional.
- `/health` continua leve e local ao processo. `/ready` verifica catalogo, ERP
  habilitado e inferencia, retornando `503` e `degraded` quando uma dependencia
  configurada nao estiver disponivel. As regressões foram adicionadas e ainda
  aguardam a rodada de testes da Prioridade 0.
- O warm-up opcional da LLM roda em tarefa de fundo depois de a aplicacao estar
  pronta; carregar um modelo grande nao pode reter o startup nem resetar
  `/health`.

## Endurecimento De Portas Aplicado Em 21/09/2026

- A inspeção da VPS encontrou Redis (`6379`), catalogo (`5433`), Ollama
  (`11434`), agente (`8001`) e Streamlit (`8501`) publicados antes da mudanca.
  O Nginx ja atende o chat por `127.0.0.1:8501`, e o `docker-comm` usa
  `127.0.0.1:8002`.
- O Compose limita os servicos de manutencao ao loopback e remove a publicacao
  do Redis. A aplicacao na VPS confirmou os listeners, o Nginx e o backend do
  ERP quente habilitado. O UFW permaneceu inativo para nao alterar portas de
  outros projetos da maquina.

## Backup Manual Mantido Sob Revisao Em 21/09/2026

- A automacao de backup e restore foi adiada. O procedimento manual revisado
  continua cobrindo catalogo, regras, fila de revisao, dataset e estado
  conversacional necessario antes de qualquer deploy ou mudanca estrutural.
- A automacao volta ao backlog somente se a frequencia de operacao ou a beta
  mostrarem que o procedimento manual deixou de ser suficiente.

## Deploy Protegido E Beta Inicial Na VPS Em 21/09/2026

- A VPS passou a expor agente (`8001`), catalogo (`5433`), Ollama (`11434`) e
  Streamlit (`8501`) somente no loopback; Redis nao possui porta publicada. O
  Nginx continuou respondendo ao dominio HTTPS do chat. O UFW permaneceu
  inativo, conscientemente, porque a maquina tambem hospeda outros projetos.
- O agente iniciou em producao com as chaves de revisao e gateway configuradas;
  catalogo, ERP quente com fallback local e UI responderam apos o deploy.
- A beta inicial pelo `docker-comm` confirmou conversa persistida no Redis,
  follow-up de selecao de filtro de oleo e desambiguacao de coxim por posicao,
  versao e candidato. Esses smoke tests confirmam fluxo e infraestrutura; a
  avaliacao comercial rotulada de ranking continua pendente.

## Fluxos De Desconhecimento E Cobertura Lexical Implementados Localmente Em 21/09/2026

- Um `nao sei` respondido a um slot governado pendente deixa de cair na LLM ou
  repetir a mesma pergunta: quando nao ha discriminador catalogado suficiente,
  o backend preserva os criterios confirmados e encaminha ao atendimento
  humano.
- O alias curto `vela`/`velas` foi incluido no catalogo de velas de ignicao
  automotivas. A extracao tambem preserva quantidade nua imediatamente antes
  do alias, sem interpretar ano ou motor como quantidade.
- Foram acrescentadas regressões unitarias e dois cenarios no dataset
  estrutural: `radiador Gol 2010 -> nao sei a motorizacao` e `4 velas NGK para
  Gol 2010 1.0`. A execucao da bateria permanece para a rodada conjunta de
  validacao solicitada pelo usuario.

## Instrumentacao E Desempate Conservador Do ERP Em 21/09/2026

- A consulta agora registra, depois da identidade de familia/codigo, candidatos
  brutos, rejeitados, filtrados e ranqueados. Rejeicoes distinguem refinamento
  do item de falha de aplicacao, e resultados finais trazem `score_breakdown`.
- O diagnostico fica nos logs e na fila interna de revisao, limitado a 50
  candidatos por etapa; o chat continua recebendo apenas os itens permitidos
  pelo contrato publico.
- Aplicacao exata segue eliminatoria. A preferencia explicita por marca de
  produto desempata candidatos; injecao, transmissao, complemento e atributos
  comerciais permanecem com peso zero ate a rodada humana de ranking.
- Foram adicionadas regressao de captura na fila e o caso ERP
  `ranking_trace_preferred_brand_and_rejections`. A execucao dos novos testes e
  da bateria foi adiada conforme solicitado pelo usuario.

## Bateria Real Com Diagnostico Correlacionado Em 22/09/2026

- A bateria passa a buscar a acao interna `search_diagnostics` na captura de
  revisao pelo `trace_id` de cada turno. Pelo `docker-comm`, ela usa o id
  devolvido pelo gateway, preservando a correlacao com o request real.
- O JSON passa a conter a trilha completa de candidatos; o Markdown e a
  comparacao humana mostram contagens, primeiro ranqueado e o estado da
  captura. O contrato publico do chat continua sem diagnostico.
- Foram adicionados testes unitarios para extracao da fila, correlacao do
  trace do gateway e renderizacao do resumo. `12` testes de
  `test_real_respond_battery.py` passaram em container.
- Uma rodada integrada de `legacy_001` retornou HTTP 200 e gerou o resumo de
  `310` candidatos brutos, `306` rejeitados, `4` filtrados e `4` ranqueados;
  artefatos locais em `.tmp/eval/real_respond_battery_agent_20260922T111922434539Z.*`.

## Troca De Familia Pendente E Regressoes Reais Em 22/09/2026

- Uma familia nova, reconhecida diretamente no catalogo durante um follow-up,
  agora substitui o item ativo antes de o proximo atributo ser aplicado. A
  regressao de `real_004` cobre `polia -> rolamentos -> 2013`.
- O catalogo recebeu aliases compostos para `bucha estabilizador` e `junta da
  tampa de valvula`; as regressoes de `real_001` e `real_046` protegem a
  decomposicao correta das familias. A extracao tambem reconhece
  `dianteiras`/`traseiras`.
- Seis testes focados passaram em container, incluindo a geracao reproduzivel
  do dataset estrutural, sem executar a bateria longa.

## Preservacao Local Do Experimento Em GPU Em 19/10/2026

- O experimento foi consolidado em
  `fine_tuning_gpu/experimento_qwen_2026-10-19/`, com indice, pesos completos
  do Qwen/Qwen2.5-7B-Instruct na revisao
  `a09a35458c702b33eeacc393d103063234e8bc28`, adapter final, checkpoints,
  dataset, codigo congelado, snapshots, logs e backup da comparacao.
- Os quatro shards base e os 43 arquivos da execucao de treino foram
  conferidos por SHA-256 contra os arquivos da VPS. A comparacao preservada
  foi conferida com 796 registros de casos e 1.169 turnos ponta a ponta,
  sem avisos operacionais. As avaliacoes anteriores de categoria ficam
  separadas em `historico_categorias/`.
- Os caminhos anteriores dentro de `fine_tuning_gpu` foram reorganizados;
  `caminhos_originais.json` registra a correspondencia. Manifestos e logs
  historicos mantem os caminhos originais. O inventario local e a verificacao
  ficam em `integridade.json` e `verificacao_pacote.json`.
- O pacote permite carregar base e adapter sem arquivos da VPS antiga;
  bibliotecas, drivers e recursos de memoria devem estar disponiveis no
  ambiente escolhido. O carregador offline teve sintaxe e ajuda conferidas,
  sem executar inferencia completa local. O modelo ativo permanece o mesmo;
  a organizacao nao desligou a instancia do provedor.
