# Integracao De Pesquisa Com O ERP

Este guia descreve a camada de integracao de pesquisa com o ERP.

Use isso no banco ERP, nao no banco local de catalogo do `docker-agent`.

Nome esperado do objeto final:
- `soccol.item_search_candidates`

## Objetivo

A primeira integracao real de busca deve retornar apenas itens candidatos:
- `item_id`
- titulo de exibicao
- score de busca calculado pela query

Esta primeira camada nao deve trazer:
- preco
- estoque
- tributacao
- WMS
- enriquecimento tecnico detalhado

Esse enriquecimento pode ficar para uma segunda consulta, depois que a lista de itens ja for conhecida.

## Por Que Criar Uma View Ou Camada Equivalente

Os dados de busca no ERP estao espalhados por varias tabelas:
- `item`
- `item_produto`
- `produto_veiculos`
- `item_pesquisa`
- `grupo_similar_item`
- `grupo_similar_outros_codigos`

Se o `docker-agent` consultar essas tabelas diretamente, a integracao fica acoplada demais aos detalhes internos do ERP.

Essa camada entrega uma linha por `id_item`, ja achatando:
- codigo e nome do item
- dimensoes de marca e modelo vindas das tabelas veiculares do ERP
- codigos do produto
- texto de aplicacao veicular
- faixa de anos
- codigos de complemento, injecao, motor e transmissao
- codigos similares
- texto auxiliar de busca

## Modulo SQL De Integracao

Arquivo principal:
- [erp_search_integration_candidates_runtime.sql](/d:/TCC/docker-agent/docs/assets/sql/erp_search_integration_candidates_runtime.sql:1)

Campos de saida mais uteis para a primeira integracao:
- `id_item`
- `cd_item`
- `candidate_title`
- `cd_original`
- `cd_fabricante`
- `vehicle_brand_names`
- `vehicle_model_names`
- `vehicle_complement_names`
- `vehicle_model_injection_names`
- `vehicle_model_motor_names`
- `vehicle_model_transmission_names`
- `vehicle_year_start`
- `vehicle_year_end`
- `vehicle_year_open_end`
- `vehicle_application_text`
- `similar_codes_text`
- `search_text`
- `pesquisa_full_text_txt`

## Observacoes Praticas

- `item_produto.obs_ficha_tecnica` e `item_pesquisa.ficha_tecnica_item` sao limpos de HTML para reuso posterior.
- `produto_veiculos` e agregado para a camada final manter uma linha por item.
- `veiculo_montadora` e `veiculo_modelo` sao resolvidos para nomes legiveis de marca e modelo.
- `grupo_similar_outros_codigos` e agregado em um unico campo textual.
- `veiculo_complemento`, `veiculo_injecao`, `veiculo_motor` e `veiculo_transmissao` sao resolvidos em nomes legiveis.
- as tabelas relacionais por modelo continuam expostas como codigos e nomes agregados.
- a camada final ja exclui itens inativos e itens com `cd_tipo = '07'`.

## Exemplo De Query De Busca

Exemplo para:
- peca: `coxim`
- modelo: `ecosport`
- ano: `2008`

```sql
WITH params AS (
    SELECT
        'coxim'::text AS part_query,
        'ford'::text AS vehicle_brand,
        'ecosport'::text AS vehicle_model,
        '1.6'::text AS vehicle_engine,
        2008::int AS vehicle_year
)
SELECT
    v.id_item,
    v.cd_item,
    v.candidate_title,
    (
        CASE
            WHEN v.cd_item ILIKE '%' || p.part_query || '%' THEN 0.35
            WHEN v.search_text ILIKE '%' || p.part_query || '%' THEN 0.25
            ELSE 0
        END
        +
        CASE
            WHEN COALESCE(v.vehicle_brand_names, '') ILIKE '%' || p.vehicle_brand || '%' THEN 0.15
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_brand || '%' THEN 0.10
            ELSE 0
        END
        +
        CASE
            WHEN COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.30
            WHEN COALESCE(v.vehicle_model_names, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.25
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_model || '%' THEN 0.20
            ELSE 0
        END
        +
        CASE
            WHEN p.vehicle_engine IS NULL THEN 0
            WHEN COALESCE(v.vehicle_model_motor_names, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.20
            WHEN COALESCE(v.vehicle_application_text, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.15
            WHEN COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_engine || '%' THEN 0.10
            ELSE 0
        END
        +
        CASE
            WHEN p.vehicle_year IS NULL THEN 0
            WHEN (
                p.vehicle_year >= COALESCE(v.vehicle_year_start, 1900)
                AND (
                    v.vehicle_year_open_end
                    OR p.vehicle_year <= COALESCE(v.vehicle_year_end, 2100)
                )
            ) THEN 0.25
            WHEN COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_year::text || '%' THEN 0.15
            ELSE 0
        END
    ) AS score
FROM soccol.item_search_candidates v
CROSS JOIN params p
WHERE v.search_text ILIKE '%' || p.part_query || '%'
  AND (
      p.vehicle_brand IS NULL
      OR COALESCE(v.vehicle_brand_names, '') ILIKE '%' || p.vehicle_brand || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_brand || '%'
  )
  AND (
      COALESCE(v.vehicle_application_text, v.aplicacoes_veiculos, '') ILIKE '%' || p.vehicle_model || '%'
      OR COALESCE(v.vehicle_model_names, '') ILIKE '%' || p.vehicle_model || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_model || '%'
  )
  AND (
      p.vehicle_engine IS NULL
      OR COALESCE(v.vehicle_model_motor_names, '') ILIKE '%' || p.vehicle_engine || '%'
      OR COALESCE(v.vehicle_application_text, '') ILIKE '%' || p.vehicle_engine || '%'
      OR COALESCE(v.pesquisa_full_text_txt, '') ILIKE '%' || p.vehicle_engine || '%'
  )
ORDER BY score DESC, v.id_item
LIMIT 20;
```

## Nome Final Esperado

Este guia assume:
- schema: `soccol`
- nome do objeto: `item_search_candidates`

Entao o uso esperado e:

```sql
SELECT * FROM soccol.item_search_candidates LIMIT 10;
```

## Limitacao Importante

Se voce quiser indices com `pg_trgm` depois, uma `VIEW` simples nao e o melhor alvo final.

Para desempenho, a evolucao mais provavel e:
1. comecar com essa estrutura de integracao
2. validar a qualidade da busca
3. se necessario, evoluir para:
   - `MATERIALIZED VIEW`, ou
   - tabela dedicada de busca no ERP com refresh periodico

Esse e o lugar certo para indexacao mais pesada e busca trigram.

## Estrutura Criada Pelo Modulo

O SQL de integracao cria:
1. `soccol.item_vehicle_model_agg_mv`
2. `soccol.item_vehicle_agg_mv`
3. `soccol.item_search_candidates_mv`
4. `soccol.item_search_candidates` como view final fina

Isso reduz agregacoes repetidas sobre `produto_veiculos` e permite indices sobre o dataset final de busca.

Ordem de refresh:

```sql
REFRESH MATERIALIZED VIEW soccol.item_vehicle_model_agg_mv;
REFRESH MATERIALIZED VIEW soccol.item_vehicle_agg_mv;
REFRESH MATERIALIZED VIEW soccol.item_search_candidates_mv;
```

## O Que Ainda Falta Definir

Esta proposta ja resolve nomes oficiais de marca e modelo por meio de:
- `veiculo_montadora`
- `veiculo_modelo`

O que ainda falta definir e a decisao de negocio sobre o peso de cada nova dimensao no ranking:
- complemento
- injecao
- motor
- transmissao

A camada final ja expoe tanto codigos quanto nomes legiveis para essas dimensoes.
