# Integracao De Pesquisa Com O ERP

## Resultados E Alcance Comercial

O runtime apresenta diretamente ate 10 candidatos. A consulta padrao busca
11 linhas para detectar excedente; esse limite nao e uma contagem total.
Acima de 10, refina por atributos confiaveis ou apresenta paginas curtas.
Ao reduzir a lista pendente a ate 10 candidatos, apresenta-os sem exigir
uma unica escolha. Candidatos sao opcoes de catalogo, nao ofertas comerciais.

`branch_id` identifica o contexto e a telemetria, mas nao filtra o SQL atual.
Preco e estoque por filial exigem integracao propria antes de serem informados.
`confidence` e um indicador heuristico nao calibrado do fluxo; `score` e
relevancia heuristica da busca. Nenhum deles e probabilidade comprovada de
encaixe. Confirmacao de aplicacao depende dos dados e da verificacao da peca.
Calibracao requer avaliacoes humanas rotuladas.

Filtros de identidade e aplicacao precedem o ranking; todos os candidatos
aprovados satisfazem esses filtros. Empates continuam possiveis. Alterar pesos
de motor, complemento, injecao e transmissao exige comparacao rotulada;
desempate estavel nao deve ser confundido com ganho de qualidade medido.

A busca usa o contrato v2 em dois objetos:

- `soccol.item_search_candidates`: uma linha por item, com identidade de familia.
- `soccol.item_search_applications`: uma linha por aplicacao da peca a um veiculo.

O DDL externo pertence a operacao do banco ERP e fica fora do Git.
A [consulta Python](../../app/infra/erp_search_query.py)
consome o mesmo contrato no ERP e no fallback local.

Ordem das colunas exportadas (tambem exigida pela carga CSV local):

- itens: `id_item`, `cd_item`, `nm_item`, `candidate_title`, `cd_grupo`,
  `cd_subgrupo`, `part_family`, `cd_original`, `cd_fabricante`, `search_text`;
- aplicacoes: `application_id`, `id_item`, `vehicle_brand`, `vehicle_model`,
  `year_start`, `year_end`, `year_open_end`, `engines`, `variants`, `injections`,
  `transmissions`, `application_text`.

Tipos, chaves e indices da copia local estao no
[bootstrap consolidado](../../db/init/pre_search_init.sql). O exportador
projeta as colunas explicitamente, mesmo se a view externa mudar sua ordem.

## Identidade Antes Do Ranking

`part_query` deve ser a familia canonica resolvida pelo catalogo. O runtime usa
os codigos de grupo/subgrupo de origem preservados em `part_family_ids`. Exige
tambem igualdade com `part_family` ou, nas especializacoes curadas de subgrupos
amplos, todos os termos significativos da familia no titulo. A consulta avulsa
sem catalogo exige igualdade do nome da familia. As comparacoes ignoram caixa,
acentos portugueses e espacos repetidos; nao aceitam substring de familia.

Assim, `radiador` nao aceita `tampa do radiador`, kit, mangueira ou suporte
classificado em outra familia. Prefixos de acessorio no titulo tambem bloqueiam
um item erroneamente classificado como a peca principal. Esses componentes continuam pesquisaveis quando
sua propria familia e solicitada. A qualidade da classificacao do subgrupo no
ERP permanece uma dependencia: titulo parecido nao substitui essa identidade.
A extracao preserva o componente em frases como `tampa do radiador` e
`kit do radiador`; um composto desconhecido nao vira a familia interna. Os
aliases de tampa e mangueira tambem estao registrados no CSV de bootstrap.

Codigo de item, original ou fabricante usa igualdade e respeita os demais
criterios fornecidos. Pedido sem identidade de peca ou codigo nao enumera o
estoque. Lado, posicao e eixo usam o nome completo e o titulo do proprio item,
pois o titulo abreviado pode omitir a direcao presente no nome completo.

## Aplicacao Veicular E Proveniencia

Cada linha de `item_search_applications` preserva:

| Campo | Origem |
| --- | --- |
| `application_id`, `id_item` | `produto_veiculos.id_geral`, `id_item` |
| `vehicle_brand`, `vehicle_model` | Dimensoes identificadas na mesma linha de `produto_veiculos` |
| `year_start`, `year_end`, `year_open_end` | Anos daquela aplicacao; `ano_final = 0` significa fim aberto |
| `engines` | `produto_veiculos_motor.id_produto_veiculos` -> `veiculo_motor` |
| `variants` | Complemento cadastrado na propria aplicacao |
| `injections`, `transmissions` | Relacoes `produto_veiculos_injecao/transmissao` por aplicacao |
| `application_text` | Texto original conservado para inspecao, sem comprovar compatibilidade |

Montadora e modelo precisam pertencer ao mesmo cadastro de veiculo. Nomes de
modelo usam igualdade: `Gol` e `Golf` sao identidades distintas. Motor usa
limites de token, permitindo `1.0` em `1.0 L 8V FLEX`, sem aceitar `11.0`.
Versao/complemento usa igualdade normalizada.

Todos os criterios veiculares sao aplicados a uma mesma linha. Nao basta que
cada criterio apareca em algum veiculo do item. Os motores e demais atributos
possiveis do modelo (`veiculo_modelo_motor` etc.) nao sao herdados pela peca.

Ano inicial conhecido e obrigatorio quando o pedido informa ano. Intervalos
fechados incluem ambos os limites. Fim aberto exige a marcacao explicita e
preserva o inicio da propria aplicacao. Fim desconhecido (`NULL`) nao significa
fim aberto. Intervalos separados continuam separados, inclusive para motores
ou versoes diferentes do mesmo modelo. Os antigos `MIN/MAX` e
`vehicle_year_open_end` agregados por item deixam de comprovar aplicacao.

A consulta devolve as aplicacoes que passaram pelos filtros e restringe os
motores/versoes exibidos ao criterio informado, inclusive quando uma aplicacao
tem varias alternativas cadastradas. Somente essas
linhas fornecem motor, versao, injecao, transmissao e rotulo de aplicacao para
`PartItem.attributes`. Texto livre e atributos de outros veiculos nao
alimentam a desambiguacao.

## Ordenacao E Limites

O ranking e o `LIMIT` operam depois da identidade e da aplicacao.
`preferred_product_brand` continua uma preferencia no titulo, sem excluir
outras marcas compativeis. Um acessorio com titulo muito parecido ou marca
preferida nao entra na lista da peca solicitada.

Cada consulta tambem produz `search_diagnostics` para log e fila interna de
revisao. A trilha inicia depois do filtro de identidade de familia ou codigo,
para que observabilidade nao enumere o inventario inteiro. Ela registra
contagens e, no maximo, 50 candidatos brutos, rejeitados, filtrados e
ranqueados. Rejeicoes informam se vieram de refinamento do item ou da
aplicacao; cada resultado final traz `score_breakdown` e o total usado na
ordenacao. O diagnostico nao pertence a resposta publica nem e garantia de
encaixe comercial.

A bateria `run_real_respond_battery` pode correlacionar essa captura ao seu
turno por `trace_id` e copiar a evidencia para os artefatos locais em
`.tmp/eval/`. Essa leitura ocorre diretamente na fila protegida de revisao;
ela nao adiciona diagnostico ao contrato HTTP do chat.

Aplicacao exata continua sendo requisito eliminatorio. Depois desse filtro,
`application_corroboration_v1` compara o pedido com o segmento do titulo que
nomeia o modelo solicitado. Intervalo fechado com anos de quatro digitos que
inclui o ano solicitado soma `0.04`; intervalos explicitos que o contradizem
subtraem `0.16`. Motor explicitamente pedido e presente no segmento soma `0.02`.
Versao explicitamente pedida, ja comprovada pela aplicacao estruturada, soma
`0.02` quando aparece no titulo (inclusive listas de versoes depois de ` - `).
Uma exclusao explicita da versao (`exceto JOY`, por exemplo) subtrai `0.16`
e e registrada como conflito de cadastro, mesmo havendo aplicacao estruturada.
Segmentos separados por ` - ` de outros modelos, intervalos
abreviados/abertos e segmentos com `exceto`, `menos` ou `sem` nao fornecem essa
evidencia de ano. Sem modelo ou em busca por codigo, a corroboracao fica neutra.

Esses ajustes sao uma heuristica inicial auditavel, nao pesos calibrados nem
prova de encaixe. Titulo sozinho nunca inclui um produto rejeitado pela
aplicacao estruturada. Uma contradicao rebaixa o candidato e fica registrada
para revisao do cadastro; nao altera o ERP. A preferencia de marca conserva
seu bonus de `0.08`. Empates restantes usam comprimento do titulo e codigo.
Injecao e transmissao permanecem sem peso adicional; ausencia desses dados
no pedido nao e motivo para favorecer uma configuracao especifica.

O diagnostico informa `ranking_version`, `backend`, criterios, posicao real,
aplicacoes que passaram pelo filtro, segmentos usados e componentes do score.
A ordem de `ranked_candidates` e exatamente a ordem retornada ao consumidor,
inclusive nos empates. A ordenacao ocorre antes do `LIMIT`.

Esta camada retorna codigo, titulo, score e atributos de desambiguacao. Preco,
estoque, tributacao e enriquecimento comercial continuam fora deste contrato.

## Instalacao No ERP

O contrato v2 exige atualizar os dois objetos e o runtime na mesma entrega.
O runtime novo nao consome os agregados v1. Quando o ERP ainda esta em v1, a
consulta falha e o fallback v2 pode atender se estiver habilitado.

O usuario informou a aplicacao do SQL v2 no banco quente em 14/09/2026.
Uma exportacao posterior confirmou acesso as duas views pelo contrato novo.
Para outra instalacao ERP, obter as definicoes junto a operacao desse banco;
um clone deste repositorio inicia o fallback, sem instalar objetos no ERP.
Guardar definicoes e imagem anterior antes de novas migracoes externas.
Agregados auxiliares v1 nao sao consumidos pelo runtime v2; sua remocao exige
verificar consumidores externos ao projeto.

Atualizacao consistente dos dados, apos a instalacao:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
REFRESH MATERIALIZED VIEW soccol.item_search_applications_mv;
REFRESH MATERIALIZED VIEW soccol.item_search_candidates_mv;
COMMIT;
```

## Snapshot Local Reproduzivel

O [exportador](../../scripts/erp/export_search_snapshot.py) consulta diretamente
as duas views instaladas no banco quente, com colunas explicitas, em uma transacao
`REPEATABLE READ, READ ONLY`, sem instalar DDL no ERP, e exporta em UTF-8
inclusive quando o servidor de origem usa WIN1252.

O runtime da busca tambem abre a conexao ao ERP com `client_encoding=UTF8`.
Isso faz o libpq converter textos e valores JSON do servidor WIN1252 antes que
o driver Python os decodifique, mantendo a consulta online no mesmo contrato
UTF-8 do exportador e do snapshot local.

O par de arquivos fica em `db/init/fallback/v2/`, acompanhado de manifesto com
versao, data, contagens e SHA-256. A carga valida ambos os checksums e a relacao
entre item e aplicacao. O CSV antigo agregado nao e reutilizado nem convertido
em relacoes inventadas.

O [bootstrap local](../../db/init/pre_search_init.sql), no bloco `ERP FALLBACK V2`,
carrega esse contrato em uma instalacao nova. Para volume existente, usar o
[instalador](../../scripts/erp/install_search_snapshot.py): primeiro validar
com rollback; depois `--apply` instala em transacao e preserva as tabelas
anteriores em um schema de backup. A fila de revisao e o catalogo nao sao
alterados. Comandos em [operacao](operational_commands.md#busca-erp-v2-e-snapshot-local).

## Regressoes E Golden Set

O [golden set ERP](../assets/datasets/erp_search_golden_set.json) contem pedidos
automotivos, criterios normalizados, fixtures adversariais e IDs esperados.
O [avaliador](../../scripts/eval/evaluate_erp_search.py) instala fixtures do
contrato em tabelas temporarias e repete os casos apos COPY de ida e volta com
a projecao do exportador. Sao 45 casos em dois backends (90 verificacoes).
Nao modifica o ERP nem os dados permanentes locais.

Para auditar tambem a proveniencia nas tabelas de origem, fornecer
`--integration-sql .tmp/sql/erp_search_integration_candidates_runtime.sql`.
Esse modo adiciona 45 verificacoes dos SELECTs marcados `BEGIN/END
CANDIDATES SELECT` e `BEGIN/END APPLICATIONS SELECT` no arquivo fornecido.
As fixtures contaminam deliberadamente atributos globais do modelo, para
detectar heranca indevida. Somente os SELECTs sao usados em tabelas temporarias;
o DDL fornecido nao e aplicado. O modo padrao valida consumo do contrato e
serializacao, sem afirmar que auditou a definicao instalada no ERP.

O caso `audit_only_real` exige somente `AUD-REAL`, rejeitando `AUD-GOLF`,
`AUD-CROSS` e `AUD-CAP`. Outros casos cobrem lacunas de anos, fim aberto,
proveniencia de atributos, limites de motor, familia, acessorios, codigo,
preferencia de marca e aplicacao antes do limite.
`ranking_trace_preferred_brand_and_rejections` tambem verifica a trilha de
candidatos e o desempate por marca preferida, sem atribuir peso especulativo a
injecao ou transmissao.

Esse golden set testa recuperacao SQL. O golden set de pre-search continua
avaliando extracao e decisao conversacional separadamente.
