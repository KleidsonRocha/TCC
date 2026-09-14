# Integracao De Pesquisa Com O ERP

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
a projecao do exportador. Sao 38 casos em dois backends (76 verificacoes).
Nao modifica o ERP nem os dados permanentes locais.

Para auditar tambem a proveniencia nas tabelas de origem, fornecer
`--integration-sql .tmp/sql/erp_search_integration_candidates_runtime.sql`.
Esse modo adiciona 38 verificacoes dos SELECTs marcados `BEGIN/END
CANDIDATES SELECT` e `BEGIN/END APPLICATIONS SELECT` no arquivo fornecido.
As fixtures contaminam deliberadamente atributos globais do modelo, para
detectar heranca indevida. Somente os SELECTs sao usados em tabelas temporarias;
o DDL fornecido nao e aplicado. O modo padrao valida consumo do contrato e
serializacao, sem afirmar que auditou a definicao instalada no ERP.

O caso `audit_only_real` exige somente `AUD-REAL`, rejeitando `AUD-GOLF`,
`AUD-CROSS` e `AUD-CAP`. Outros casos cobrem lacunas de anos, fim aberto,
proveniencia de atributos, limites de motor, familia, acessorios, codigo,
preferencia de marca e aplicacao antes do limite.

Esse golden set testa recuperacao SQL. O golden set de pre-search continua
avaliando extracao e decisao conversacional separadamente.
