# Progresso Do Projeto

Estado em 14/09/2026. Historico de problemas, benchmarks e relatorios em
[HISTORICO.md](HISTORICO.md); pendencias e criterios de aceite em
[TODO.md](TODO.md). Resultados locais nao encerram a validacao na VPS.

## Estado Atual

- API `/respond` integra catalogo PostgreSQL, extracao deterministica,
  `deterministic_ask`, `deterministic_bypass` e LLM residual via Ollama.
- Busca e desambiguacao usam candidatos reais e estado conversacional
  persistido pelo `docker-comm` no Redis. Contrato admite `items[]`, com
  correcoes por item ainda pendentes no backlog.
- Revisao humana por conversa/turno, historico de revisoes, promocao e
  exportacao do dataset implementados. Trainer LoRA/QLoRA preparado;
  ainda sem evidencia de run concluida ou de ganho de adapter.

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

## Pendencias Principais

Negacao e conflitos, identidade/gate por item, invalidacao de candidatos,
indisponibilidade do ERP, concorrencia e acesso administrativo permanecem
bloqueadores. Tambem faltam motor textual, confirmacao de familia, avaliacao
comercial mais forte, paridade treino/runtime e validacao na VPS.
O [TODO](TODO.md) concentra o trabalho restante; reorganizar arquivos nao
altera a classificacao de prontidao comercial.
