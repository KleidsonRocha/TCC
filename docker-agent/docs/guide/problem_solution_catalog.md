# Catalogo Geral De Problemas E Solucoes

Este documento consolida os principais problemas tecnicos ja encontrados no projeto, as causas entendidas e as solucoes adotadas. A organizacao aqui e por tema, nao por data.

Ele substitui a leitura cronologica quando o objetivo e entender rapidamente:

- o que ja foi resolvido
- o que foi apenas mitigado
- o que ainda segue aberto

Base de consolidacao:

- `Documents/historico_problemas_e_solucoes_2026-03-17.md`
- ajustes posteriores incorporados diretamente no `docker-agent`

## 1. Infraestrutura E Bootstrap

### Problema

O projeto precisava subir de forma reproduzivel, sem depender de passos manuais dispersos para schema, seeds e credenciais.

### Causas

- credenciais sensiveis nao podiam ir para o repositorio
- havia risco de proliferar caminhos paralelos de carga do catalogo
- o TCC precisava de uma trilha simples de reproducao

### Solucoes adotadas

- parametrizacao do ambiente via `.env` e `docker-compose.yml`
- consolidacao do bootstrap em um unico arquivo:
  - `db/init/pre_search_init.sql`
- seeds operacionais padronizados em:
  - `db/init/csv/`
- fluxo principal de reaplicacao simplificado para recriar o banco a partir do bootstrap

### Status

- resolvido para o fluxo principal atual

## 2. Busca ERP E Desempenho SQL

### Problema

A primeira versao da busca no ERP era lenta demais para uso em runtime.

### Causas

- agregacoes pesadas em tempo de consulta
- joins extensos
- campos textuais muito grandes
- view original fazendo trabalho demais para consultas simples

### Solucoes adotadas

- reestruturacao da busca em camadas com materializacao intermediaria
- uso de uma view final fina sobre estruturas otimizadas
- validacao com consultas reais do dominio, nao apenas `LIMIT 10`

### Resultado observado

- a busca no ERP ficou viavel para runtime
- o gargalo principal deixou de ser o banco e passou a ser a LLM

### Status

- resolvido no aspecto de viabilidade operacional
- ranking e relevancia fina ainda seguem abertos

## 3. Integracao Real Com O ERP

### Problema

O fluxo principal ainda dependia de mock, mesmo com a busca real ja disponivel.

### Causas

- runtime ainda acoplado a implementacoes de teste
- integracao real nao estava no caminho padrao de execucao

### Solucoes adotadas

- implementacao de backend real de busca no ERP
- integracao do `search_parts` ao fluxo principal
- tratamento de indisponibilidade da busca

### Status

- resolvido

## 4. Estado Conversacional E Follow-up

### Problema

Respostas curtas como `1.6`, `dianteiro` ou `traseiro` podiam perder o contexto coletado no turno anterior.

### Causas

- dependencia excessiva de `last_messages` em texto bruto
- inferencia repetida da LLM sem memoria estruturada fora dela

### Solucoes adotadas

- introducao de `conversation_state` no contrato entre `docker-comm` e `docker-agent`
- persistencia desse estado por conversa no `docker-comm`
- merge defensivo entre estado anterior, seed deterministico e saida da LLM

### Status

- resolvido estruturalmente

## 5. Ruido De Contexto Na Extracao

### Problema

Mensagens do assistente contaminavam a extracao lexical ao reconstruir contexto.

### Causas

- o extractor podia reaproveitar texto gerado pelo proprio sistema

### Solucoes adotadas

- uso apenas de mensagens com `role=user` na montagem do contexto auxiliar

### Status

- resolvido

## 6. Pergunta Fixa Errada Em Multiplos Resultados

### Problema

O fluxo perguntava motorizacao de forma fixa quando havia muitos resultados, mesmo que esse nao fosse o melhor discriminador.

### Causas

- branch de multiplos resultados acoplado a uma pergunta fixa por `engine`

### Solucoes adotadas

- remocao da pergunta fixa
- retorno de `show_items` com desambiguacao pendente no estado conversacional

### Status

- resolvido

## 7. Cobertura Lexical E Alias

### Problema

Variacoes simples de escrita, singular/plural e nomes de mercado nao casavam com o catalogo.

### Causas

- dependencia de match exato no extractor
- cobertura insuficiente de aliases no catalogo

### Solucoes adotadas

- criacao e carga de `pre_search_part_alias.csv`
- enriquecimento de `pre_search_part_alias`
- ampliacao da cobertura lexical para `part_query`
- normalizacao textual consistente no extractor

### Status

- resolvido como base operacional
- curadoria incremental continua sendo trabalho permanente

## 8. Typos E Fuzzy Conservador

### Problema

Typos simples ainda escapavam do reconhecimento mesmo com alias curado.

### Causas

- o extractor operava apenas por casamento exato
- erros pequenos como transposicao de letras quebravam o reconhecimento

### Solucoes adotadas

- fallback fuzzy conservador para `part_query`
- thresholds e guardrails para reduzir falso-positivo
- manutencao da logica: fuzzy ajuda a reconhecer, mas nao libera `search` sozinho

### Status

- resolvido para `part_query`
- expansao para outros campos ainda e opcional e precisa de calibracao

## 9. Latencia Da LLM

### Problema

A chamada ao Ollama passou a dominar o tempo total da resposta.

### Causas

- unload do modelo apos periodo ocioso
- custo alto de inferencia mesmo com o modelo carregado

### Solucoes adotadas

- bateria de benchmark dedicada para latencia
- configuracao de `LLM_KEEP_ALIVE=1h`
- warmup no startup da aplicacao
- instrumentacao do comportamento antes/depois de idle

### Resultado observado

- a degradacao apos idle foi mitigada
- a primeira chamada util ficou protegida pelo warmup
- ainda existe latencia residual alta com o modelo quente

### Status

- mitigado
- segue como frente secundaria de otimizacao

## 10. Gate De Liberacao Para `search`

### Problema

Alguns casos sao liberados para busca cedo demais, com poucos discriminadores.

### Causas

- score minimo global permissivo
- pesos altos para `part_query` e `vehicle_model`
- regras obrigatorias ainda incompletas por familia

### Solucoes adotadas

- o backend ja recalcula score, `missing_fields` e merge defensivo apos a LLM
- a calibracao fina ainda segue em backlog

### Status

- aberto

## 11. Escolha Da Proxima Pergunta

### Problema

A proxima pergunta nem sempre e o dado mais util para destravar `search`.

### Causas

- politica de priorizacao ainda incompleta
- dependencia da combinacao entre regras, seed e interpretacao da LLM

### Solucoes adotadas

- reforco do estado conversacional
- melhoria da cobertura lexical para reduzir perguntas desnecessarias

### Status

- aberto

## 12. Regras Obrigatorias Por Familia

### Problema

Nem sempre os slots obrigatorios de uma familia condizem com a pergunta esperada ao usuario.

### Causas

- necessidade de auditar `needs_side`, `needs_position`, `needs_axle`, `needs_engine` e `needs_variant`
- inconsistencias entre significado de eixo, posicao e lado

### Solucoes adotadas

- catalogo de regras separado por familia
- backlog especifico para revisar essas familias com maior volume

### Status

- aberto

## 13. Avaliacao E Benchmark

### Problema

O projeto precisava de avaliacao repetivel para comparar comportamento, tuning e modelos.

### Causas

- sem datasets curados, qualquer ajuste ficava dependente de teste manual

### Solucoes adotadas

- `pre_search_eval_dataset_mvp.json` para avaliacao funcional rapida
- `pre_search_num_predict_golden_set.json` para benchmark mais estavel
- scripts dedicados para avaliacao, benchmark de `num_predict` e latencia
- fila de revisao para capturar conversas reais e promover exemplos

### Status

- resolvido como base
- volume de dados reais ainda pode crescer

## 14. Fine-Tuning E Evolucao De Modelo

### Problema

Era preciso preparar o projeto para melhoria de modelo sem acoplar o runtime ao ambiente pesado de treino.

### Causas

- treino exige GPU, dependencias proprias e pipeline separado
- o runtime da API precisa continuar simples

### Solucoes adotadas

- scripts de exportacao, revisao, empacotamento e ciclo de promocao em `scripts/training/`
- ambiente de treino separado em `trainer/`
- uso de adapter LoRA/QLoRA fora do runtime principal

### Status

- resolvido estruturalmente

## 15. Organizacao Do Repositorio

### Problema

O repositorio acumulou scripts e artefatos auxiliares que nao faziam mais parte do fluxo real do projeto.

### Causas

- experimentos validos durante a evolucao ficaram misturados com o caminho operacional oficial

### Solucoes adotadas

- manutencao do bootstrap diretamente em `db/init/`
- remocao de scripts auxiliares de carga/manual import fora do fluxo principal
- remocao de geradores e analises que nao entraram no ciclo oficial atual
- concentracao da documentacao normativa em `docs/guide/` e `docs/training/`

### Status

- resolvido para a organizacao atual do TCC

## Resumo Executivo

### Estruturalmente resolvido

- bootstrap do banco e reproducao da stack
- integracao real com ERP
- memoria conversacional fora da LLM
- extracao lexical base com aliases e fuzzy conservador para `part_query`
- datasets e trilha de avaliacao
- pipeline separado de treino

### Mitigado, mas nao zerado

- latencia do validator com Ollama

### Principalmente aberto

- gate de liberacao para `search`
- escolha da proxima pergunta
- calibracao de regras obrigatorias por familia
- refinamento de ranking e relevancia no ERP
