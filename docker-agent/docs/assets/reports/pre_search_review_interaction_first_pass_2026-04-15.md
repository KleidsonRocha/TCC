# Revisao Inicial Da `pre_search_review_interaction`

## Origem

Arquivo analisado:
- `C:\Users\Desktop\Downloads\pre_search_review_interaction.sql`

Data da analise:
- `2026-04-15`

## Resumo Executivo

Foi feita uma primeira passagem manual sobre o dump da tabela `pre_search_review_interaction`.

Resumo encontrado:
- `76` registros
- `47` conversas
- `76` registros com `review_status = 'pending'`
- `9` registros com `final_handoff_required = true`

Duplicidades exatas encontradas:
- `2x` `whatsapp:conv-ask-011` com a mesma mensagem `coxim ecosport`
- `2x` `conv-001` com a mesma mensagem `2008`
- `2x` `whatsapp:conv-ask-020` com a mesma mensagem `poderia me ver uma suspenção do gol 2008 1.6`
- `2x` `whatsapp:conv-ask-021` com a mesma mensagem `poderia me ver uma suspencao do gol 2008 1.6`

Observacao importante:
- o dump nao contem a coluna `id`
- para revisar manualmente no banco, o ideal e localizar cada linha por `conversation_id + created_at`

## Como Usar Esta Revisao

Esta revisao nao substitui a decisao humana final.
Ela serve como uma triagem inicial para acelerar o preenchimento de:
- `reviewed_decision`
- `reviewed_criteria`
- `reviewed_missing_fields`
- `reviewed_question_key`
- `reviewed_question_prompt`
- `reviewed_question_options`
- `reviewed_notes`
- `reviewed_by`

Os casos abaixo foram classificados em:
- `alta confianca`: correcoes fortemente apoiadas pelas regras do projeto
- `media confianca`: correcoes provaveis, mas que pedem confirmacao funcional

## Casos De Alta Confianca

### 1. `real-radiador-001`

Sequencia:
- `2026-03-25 16:43:45.725525-03` `radiador gol 2010`
- `2026-03-25 16:44:30.470602-03` `1.0`

Leitura:
- o primeiro turno esta coerente como `ask` por `engine`
- o segundo turno esta coerente como `search`

Revisao sugerida:
- manter o primeiro como `reviewed_decision = ask`
- manter `reviewed_missing_fields = ["engine"]`
- manter `reviewed_question_key = engine`
- manter `reviewed_question_prompt = "Qual a motorizacao do veiculo?"`
- no segundo turno, manter `reviewed_decision = search`

### 2. `real-coxim-001`

Sequencia:
- `2026-03-25 16:45:12.727864-03` `coxim amortecedor ecosport 2008`
- `2026-03-25 16:46:05.539207-03` `zetec rocam`

Leitura:
- o primeiro turno como `ask` por `engine` parece coerente
- o segundo turno continua em `ask` por `engine`, mesmo apos o usuario informar o motor

Revisao sugerida:
- primeiro turno: manter `ask`
- segundo turno: corrigir para `reviewed_decision = search`
- segundo turno: usar `reviewed_criteria` contendo pelo menos:
  - `part_query = "coxim amortecedor"`
  - `vehicle_model = "Ecosport"`
  - `vehicle_year = 2008`
  - `engine = "Zetec Rocam"`

Notas:
- este e um falso negativo claro de follow-up

### 3. `conv-coxim-ecosport-follow-text-001`

Sequencia:
- `2026-03-25 17:33:02.248144-03` `coxim amortecedor ecosport 2008`
- `2026-03-25 17:44:02.490075-03` `zetec rocam`

Leitura:
- mesmo padrao do caso anterior

Revisao sugerida:
- primeiro turno: manter `ask`
- segundo turno: corrigir para `search`
- preencher `reviewed_criteria` com `engine = "Zetec Rocam"`

### 4. `real-filtro-001`

Registro:
- `2026-03-25 16:47:27.736898-03` `filtro de oleo gol 2010`

Leitura:
- o sistema perguntou `axle`, o que nao faz sentido para `filtro de oleo`
- o slot faltante correto tende a ser `engine`

Revisao sugerida:
- `reviewed_decision = ask`
- `reviewed_criteria = {"part_query":"filtro de oleo","vehicle_model":"Gol","vehicle_year":2010}`
- `reviewed_missing_fields = ["engine"]`
- `reviewed_question_key = "engine"`
- `reviewed_question_prompt = "Qual a motorizacao do veiculo?"`

### 5. `conv-filtro-oleo-gol-follow-001`

Sequencia:
- `2026-03-25 17:28:25.175207-03` `filtro de oleo gol 2010`
- `2026-03-25 17:38:31.103057-03` `dianteiro`

Leitura:
- o primeiro turno pergunta `axle`, o que parece errado
- o segundo turno herda esse erro e degrada para um `search` improprio seguido de `handoff`

Revisao sugerida:
- primeiro turno:
  - `reviewed_decision = ask`
  - `reviewed_missing_fields = ["engine"]`
  - `reviewed_question_key = "engine"`
  - `reviewed_question_prompt = "Qual a motorizacao do veiculo?"`
- segundo turno:
  - nao promover para treino na forma atual
  - idealmente revisar como caso invalido de follow-up, porque a resposta `dianteiro` responde a uma pergunta errada

### 6. `conv-filtro-comb-gol-follow-001`

Sequencia:
- `2026-03-25 17:29:48.79337-03` `filtro de combustivel gol 2010`
- `2026-03-25 17:40:08.175599-03` `esquerdo`

Leitura:
- o primeiro turno pergunta `side`, o que nao parece coerente para `filtro de combustivel`
- o slot mais plausivel e `engine`

Revisao sugerida:
- primeiro turno:
  - `reviewed_decision = ask`
  - `reviewed_missing_fields = ["engine"]`
  - `reviewed_question_key = "engine"`
  - `reviewed_question_prompt = "Qual a motorizacao do veiculo?"`
- segundo turno:
  - nao promover para treino na forma atual

### 7. `conv-filtro-ar-gol-follow-001`

Sequencia:
- `2026-03-25 17:30:28.824539-03` `filtro ar motor gol 2010`
- `2026-03-25 17:40:51.634684-03` `dianteiro`

Leitura:
- o primeiro turno pergunta `axle`, o que parece incorreto para `filtro ar motor`
- o slot plausivel e `engine`

Revisao sugerida:
- primeiro turno:
  - `reviewed_decision = ask`
  - `reviewed_missing_fields = ["engine"]`
  - `reviewed_question_key = "engine"`
  - `reviewed_question_prompt = "Qual a motorizacao do veiculo?"`
- segundo turno:
  - nao promover para treino na forma atual

### 8. `conv-generic-part-follow-001`

Sequencia:
- `2026-03-25 17:34:15.740631-03` `quero uma peca`
- `2026-03-25 17:45:26.832098-03` `radiador gol 2010`

Leitura:
- o primeiro turno como `ask` por `part_query` esta correto
- o segundo turno como `ask` por `engine` tambem parece correto

Revisao sugerida:
- manter os dois registros
- este e um bom candidato de multi-turno para promocao

## Casos De Media Confianca

### 9. `real-bandeja-001`

Registro:
- `2026-03-25 16:48:05.528412-03` `bandeja ecosport 2008 eixo dianteiro`

Leitura:
- o sistema foi para `search` e terminou em `handoff`
- pela regra estrutural do projeto, `bandeja` tende a depender de `side`
- o usuario ja informou `axle/position` com `dianteiro`, mas nao informou lado

Revisao sugerida:
- provavelmente revisar como `ask`
- `reviewed_missing_fields = ["side"]`
- `reviewed_question_key = "side"`
- `reviewed_question_prompt = "Qual lado da bandeja voce precisa, esquerdo ou direito?"`

### 10. `conv-bandeja-ecosport-follow-001`

Sequencia:
- `2026-03-25 17:29:09.063765-03` `bandeja ecosport 2008`
- `2026-03-25 17:39:25.559475-03` `dianteiro`

Leitura:
- no primeiro turno o sistema perguntou `axle`, mas para `bandeja` a lacuna mais plausivel e `side`
- no segundo turno ele passou a pedir `engine`, o que tende a ser ruido derivado da primeira pergunta errada

Revisao sugerida:
- primeiro turno:
  - revisar para `ask` por `side`
- segundo turno:
  - provavelmente manter `ask`, mas por `side`, nao por `engine`
- este caso merece confirmacao funcional antes de promover

### 11. `conv-farol-gol-follow-001`

Sequencia:
- `2026-03-25 17:31:40.510811-03` `farol gol 2010`
- `2026-03-25 17:42:24.736125-03` `esquerdo`

Leitura:
- o primeiro turno foi para `search` sem pedir `side`
- para `farol`, o lado costuma ser relevante

Revisao sugerida:
- primeiro turno:
  - revisar para `ask`
  - `reviewed_missing_fields = ["side"]`
  - `reviewed_question_key = "side"`
  - `reviewed_question_prompt = "Qual lado do farol voce precisa, esquerdo ou direito?"`
- segundo turno:
  - provavelmente `search`
- confirmar no negocio se `vehicle_year + model + side` ja bastam

### 12. `real-pastilha-001` e familia `pastilha`

Registros correlatos:
- `real-pastilha-001`
- `conv-pastilha-gol-direct-001`
- `conv-pastilha-gol-short-001`
- `conv-pastilha-gol-alias-001`
- `conv-pastilha-gol-typo-001`
- `conv-pastilha-gol-follow-001`

Leitura:
- no SQL do projeto, `pastilha de freio` aparece como peca dependente de `position`
- varios desses casos foram aceitos como `search` sem pedir `front/rear`

Revisao sugerida:
- revisar com prioridade
- hipoteses mais provaveis:
  - `pastilha ... 2010 1.0` sem `position` deveria ser `ask`
  - `reviewed_missing_fields = ["position"]`
  - `reviewed_question_key = "position"`
  - `reviewed_question_prompt = "A pastilha e dianteira ou traseira?"`

Observacao:
- aqui vale validar com seu criterio de negocio antes de promover em lote

### 13. `conv-disco-gol-*`

Registros:
- `conv-disco-gol-direct-001`
- `conv-disco-gol-follow-001`

Leitura:
- o sistema ja considera `engine` faltante
- nao esta claro, so pelo dump, se `disco de freio` tambem exigiria `position`

Revisao sugerida:
- manter em fila de confirmacao funcional
- nao promover em lote sem decisao sua

## Casos Bons Para Promocao Rapida

Estes parecem bons candidatos para entrar no dataset com pouca intervencao:
- `real-radiador-001`
- `conv-radiador-gol-follow-001`
- `conv-radiador-ecosport-follow-001`
- `conv-radiador-focus-follow-001`
- `conv-generic-part-follow-001`
- `whatsapp:conv-ask-013` com ajuste cuidadoso no segundo turno
- `real-coxim-003`

## Casos Que Eu Evitaria Promover Agora

Porque parecem contaminados por pergunta errada anterior ou por regra ainda instavel:
- `conv-filtro-oleo-gol-follow-001` segundo turno
- `conv-filtro-comb-gol-follow-001` segundo turno
- `conv-filtro-ar-gol-follow-001` segundo turno
- `conv-001` em geral, porque mistura varios cenarios syntheticos numa mesma conversa
- duplicatas exatas da mesma mensagem

## Duplicidades Recomendadas

Sugestao operacional:
- revisar apenas uma das copias
- marcar a duplicata como `discarded`

Duplicatas mapeadas:
- `whatsapp:conv-ask-011` `coxim ecosport`
- `conv-001` `2008`
- `whatsapp:conv-ask-020` `poderia me ver uma suspenção do gol 2008 1.6`
- `whatsapp:conv-ask-021` `poderia me ver uma suspencao do gol 2008 1.6`

## Estrategia Recomendada De Revisao

Ordem sugerida:

1. revisar e promover os casos de radiador multi-turno
2. corrigir os casos de filtro com pergunta errada (`axle` ou `side`)
3. revisar a familia `bandeja`
4. revisar a familia `pastilha`
5. descartar duplicatas

## Proxima Etapa

Depois da revisao manual no banco:
- promover so os casos revisados com alta confianca
- exportar o dataset
- rodar benchmark antes de treinar um lote maior
