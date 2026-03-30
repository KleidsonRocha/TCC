# Analise De Produto - Bateria Real `/respond` - 2026-03-26

## Base analisada

Esta analise usa como base a bateria real executada em 2026-03-25:

- arquivo fonte: `docs/assets/reports/real_respond_battery_2026-03-25.json`
- total de casos: `50`
- casos HTTP `200`: `48`
- casos HTTP `400`: `2`

Objetivo desta leitura:

- avaliar se as perguntas feitas pela IA fizeram sentido
- avaliar se o tempo de resposta esta aceitavel
- identificar logicas erradas ou inconsistentes
- avaliar o estado atual do produto do ponto de vista de uso real

## Veredito Executivo

O produto ja demonstra um nucleo funcional real:

- entende parte relevante dos pedidos
- conduz varios fluxos de `ask -> follow-up -> search`
- tolera alguns erros de digitacao
- consulta ERP real e devolve itens reais

Mas ele ainda nao esta pronto para ser tratado como um atendimento confiavel de autopecas.

Os dois maiores riscos de produto hoje sao:

- latencia operacional muito alta
- liberacao de `search` em cenarios em que a IA ainda nao entendeu a peca de forma suficientemente segura

Em termos de maturidade, o estado atual parece de `prova funcional integrada`, nao de `produto pronto para operacao`.

## O Que Ja Funciona Bem

### 1. Perguntas basicas de complemento fazem sentido na maior parte dos casos

Nas `18` respostas com `request_info`, a maioria foi coerente com o objetivo da busca.

Exemplos bons:

- `radiador gol 2010` -> pergunta por motorizacao
- `coxim amortecedor ecosport 2008` -> pergunta por motor
- `quero uma peca` -> pergunta qual peca
- `preciso de ajuda com uma peca do gol` -> pergunta qual peca do Gol
- `bandeja ecosport 2008` -> pergunta por eixo
- follow-up `dianteiro` nesse mesmo fluxo -> pergunta por motor

Leitura de produto:

- o fluxo conversacional basico existe
- ha memoria de contexto suficiente para continuar a conversa
- o produto nao esta completamente "cego"; ele consegue destravar parte dos fluxos reais

### 2. O sistema lida razoavelmente com alguns typos

Exemplos bons:

- `rdiador ecosport 2008 1.6`
- `coxin amortecedor ecosport 2008 1.6`
- `rdiador gol 2010`

Leitura de produto:

- ha valor real na extracao lexical/fuzzy atual
- para erros simples e previsiveis, o produto ja esta acima do baseline trivial

### 3. Follow-up numerico funciona melhor do que um chatbot raso

Exemplos bons:

- `radiador gol 2010` -> `1.0` -> busca real
- `radiador focus 2010` -> `1.6` -> busca real
- `bandeja ecosport 2008` -> `dianteiro` -> pergunta por motor

Leitura de produto:

- o produto nao esta apenas respondendo uma mensagem isolada
- existe continuidade de estado suficiente para uma conversa operacional curta

## Principais Problemas De Produto

### 1. Latencia esta fora do aceitavel para atendimento

Numeros observados nos `48` casos validos:

- latencia minima: `31639.51 ms`
- latencia mediana: `39940.01 ms`
- latencia media: `39398.82 ms`
- p95 aproximado: `49335.51 ms`
- maxima: `93893.93 ms`
- `48/48` respostas validas ficaram acima de `30s`
- `10/48` ficaram acima de `45s`

Leitura de produto:

- isso nao esta aceitavel para uso operacional continuo
- mesmo para um atendente interno, esperar `30s` a `50s` por turno quebra o fluxo de atendimento
- o caso de `93.89s` e severo o bastante para parecer travamento ou falha ao usuario

Conclusao:

- latencia hoje e problema de produto de primeira ordem, nao apenas problema tecnico de infraestrutura

### 2. Ha familias sendo liberadas para `search` cedo demais

Esse e o problema mais perigoso depois da latencia, porque afeta confianca comercial.

Casos evidentes:

- `disco de freio gol 2010` foi direto para `show_items`, mesmo sendo uma familia que na seed versionada exige mais discriminacao
- `farol gol 2010` foi direto para `show_items` sem perguntar lado
- `pstilhas gol 2010` foi para `no_match` em vez de pedir complemento

Leitura de produto:

- o sistema ainda esta disposto demais a "tentar buscar" antes de ter certeza da familia e dos discriminadores
- isso parece coerente com o threshold atual de liberacao, que soma `part_query + vehicle_model` e frequentemente chega perto do necessario para buscar
- quando a familia nao esta canonizada corretamente, as regras obrigatorias deixam de proteger o fluxo

Impacto:

- aumenta ruido de resultado
- aumenta falso negativo por `no_match`
- transmite sensacao de que o produto "entendeu", quando na pratica ele ainda nao entendeu direito

### 3. Ha evidencia de quebra de canonizacao do `part_query`

Casos importantes:

- `disco de freio gol 2010` ficou com `part_query = "disco de freio"`
- `pstilhas gol 2010` ficou com `part_query = "pstilhas"`
- `farol gol 2010` ficou com `part_query = "farol"`

Leitura de produto:

- o sistema esta aceitando `part_query` livre demais na resposta final
- quando esse texto final nao bate exatamente com a familia canonica do catalogo, as regras de `needs_engine`, `needs_side`, `needs_axle` e afins podem nao ser aplicadas

Efeito pratico:

- `pstilhas` nao herda a regra de `pastilhas de freio`
- `disco de freio` pode nao herdar a regra de `discos de freio`
- uma familia nao curada como `farol` pode cair em busca direta sem guardrails adequados

Do ponto de vista de produto, isso e grave porque a conversa parece correta na superficie, mas a camada de protecao de negocio pode estar sendo ignorada.

### 4. Existe pelo menos um caso real de `part_code` indevido

Caso observado:

- `pastilha de freio 2010 1.0` terminou com `part_code = "FREIO-2010"`

Leitura de produto:

- isso nao pode acontecer em um fluxo confiavel
- `part_code` e um campo muito forte, porque muda o comportamento da busca e pode enviesar o SQL para match exato

Impacto:

- risco de `no_match` artificial
- risco de busca enviesada para codigo inexistente
- perda de confianca na resposta

Observacao:

- nesta passada eu nao fechei a trilha exata de geracao desse valor
- mas a evidencia do caso real ja basta para tratar isso como defeito prioritario

### 5. Algumas perguntas fazem pouco sentido do ponto de vista de negocio

Casos ruins:

- `filtro de oleo gol 2010` -> perguntou `axle`
- `filtro ar motor gol 2010` -> perguntou `axle`
- `filtro de combustivel gol 2010` -> perguntou `side`

Leitura de produto:

- para um usuario comum, essas perguntas soam erradas
- para um atendente experiente de autopecas, elas tambem soam suspeitas

Conclusao:

- aqui o problema e mais de catalogo/regra do que de LLM
- a IA esta sendo coerente com regras que parecem mal cadastradas

### 6. O fluxo com motor textual ainda falha em um caso muito real

Caso observado:

- `coxim amortecedor ecosport 2008` -> pergunta por motor
- usuario responde `zetec rocam`
- sistema repete a pergunta de motor em vez de seguir para busca

Leitura de produto:

- esse comportamento quebra a naturalidade da conversa
- um usuario humano considera `zetec rocam` uma resposta valida
- repetir a mesma pergunta passa sensacao de "nao entendeu nada"

Conclusao:

- hoje o produto entende melhor motor numerico do que motor textual
- isso precisa subir de prioridade porque ocorre em linguagem real de oficina e balcão

### 7. O ranking do ERP ainda esta ruidoso demais

Exemplos:

- `radiador gol 2010 1.0` trouxe radiador, mas tambem `kit coxim radiador`, `tampa radiador` e `mangueira`
- `pastilha de freio gol 2010 1.0` trouxe aplicacoes antigas e modelos correlatos
- `farol gol 2010` trouxe `parafuso do farol` e `lampada`, nao o conjunto do farol

Leitura de produto:

- a busca esta viva, mas ainda nao esta precisa
- o produto consegue "achar coisas relacionadas", nao necessariamente a peca certa

Impacto:

- exige muito trabalho manual do usuario
- aumenta risco de selecao errada
- reduz confianca nas primeiras opcoes listadas

### 8. Quando ha muitos resultados, o produto ainda nao conduz a desambiguacao

Estado atual observado:

- o sistema responde com `show_items`
- grava `pending_slot = result_disambiguation`
- mas nao faz uma pergunta operacional clara sobre como refinar

Leitura de produto:

- a conversa para no meio do caminho
- o produto mostra a lista, mas nao ensina o proximo passo
- isso e especialmente ruim quando a lista ja vem ruidosa

Do ponto de vista de UX, ainda falta o fluxo "encontrei varios resultados, agora preciso deste discriminador para reduzir".

### 9. O tratamento de `no_match` e generico demais

Casos como:

- `dianteiro` no follow-up de `filtro de oleo`
- `esquerdo` no follow-up de `filtro de combustivel`
- `esquerdo` no follow-up de `farol`

Resposta observada:

- sempre volta algo como `me informe modelo, ano e motorizacao`

Leitura de produto:

- isso ignora o estado atual da conversa
- o usuario ja tinha informado parte desses dados
- a resposta soa regressiva e pouco inteligente

Impacto:

- frustra o usuario
- joga fora o contexto acumulado
- aumenta a chance de abandono ou transferencia prematura

### 10. Ha problema visivel de encoding em parte das respostas e titulos

Exemplos observados:

- `veÃ­culo`
- `AUTOMÃTICO`
- `Ã“LEO`

Leitura de produto:

- isso piora muito a percepcao de qualidade
- mesmo quando a logica esta correta, o texto parece quebrado

Isso nao e apenas detalhe estetico:

- reduz confianca
- dificulta leitura de item
- passa sensacao de sistema mal acabado

## Avaliacao Das Perguntas Feitas Pela IA

Resumo pratico:

- `14` das `18` perguntas de complemento pareceram boas ou aceitaveis
- `4` das `18` foram claramente ruins do ponto de vista de negocio ou entendimento

Perguntas boas:

- complemento por motor em radiador, coxim e pastilha
- complemento por eixo em bandeja
- complemento por tipo de peca em pedidos genericos

Perguntas ruins:

- `axle` para filtro de oleo
- `axle` para filtro de ar do motor
- `side` para filtro de combustivel
- repeticao de pergunta de motor apos `zetec rocam`

Conclusao:

- a IA pergunta coisas uteis com frequencia razoavel
- mas ainda existe um grupo pequeno e muito danoso de perguntas "erradas com conviccao"
- esse grupo precisa ser tratado primeiro, porque afeta diretamente confianca do produto

## Leitura Das Logicas Atuais

### Threshold e liberacao de busca

O threshold padrao ainda esta em `70`, com pesos fortes para:

- `part_query = 45`
- `vehicle_model = 35`
- `vehicle_year = 20`
- `engine = 20`

Leitura:

- `part_query + vehicle_model` ja soma `80`
- isso ajuda a explicar por que alguns casos vao para `search` cedo demais

### Regra de negocio depende de nome canonico de familia

As regras de obrigatoriedade funcionam por membership exato da familia em conjuntos como:

- `needs_engine`
- `needs_side`
- `needs_position`
- `needs_axle`

Leitura:

- se o `part_query` final nao estiver canonizado corretamente, a regra pode nao disparar
- isso ajuda a explicar escapes como `pstilhas`, `disco de freio` e possivelmente `farol`

### `show_items` e `confidence` ainda estao simplificados demais

Hoje a camada de orquestracao:

- usa resposta fixa para `0`, `1` ou `N` itens
- usa `confidence` fixa para `no_match`, item unico e muitos itens

Leitura:

- essa `confidence` nao representa a qualidade real da busca
- o downstream nao deveria confiar muito nela no estado atual

## O Que Vem De Catalogo E O Que Vem De Logica

Problema mais de catalogo:

- `filtro de oleo` pedindo `axle`
- `filtro de ar do motor` pedindo `axle`
- `filtro de combustivel` pedindo `side`

Problema mais de logica/orquestracao:

- `part_query` nao canonizado escapando das regras
- `part_code` indevido
- repeticao de pergunta para motor textual
- falta de pergunta de desambiguacao apos `show_items`
- resposta generica demais em `no_match`

Problema mais de busca/ranking:

- itens relacionados aparecendo como se fossem alternativas centrais
- muitos empates de score
- pouca separacao entre item exato e item apenas correlato

## Prioridades Recomendadas

### Prioridade 1

- impedir `part_query` livre nao canonico de pular as regras do catalogo
- bloquear totalmente qualquer `part_code` inventado
- revisar imediatamente as regras de `filtro de oleo`, `filtro de ar do motor` e `filtro de combustivel`

### Prioridade 2

- melhorar entendimento de motor textual em follow-up
- tornar a resposta de `no_match` contextual, usando o estado ja acumulado
- adicionar pergunta real de desambiguacao quando houver muitos itens

### Prioridade 3

- reduzir ruido do ranking ERP
- melhorar encoding/text normalization nos titulos e respostas
- recalibrar a latencia com caminho deterministico para casos obvios

## Conclusao Final

Se eu estivesse como dono do produto hoje, eu diria:

- o produto prova que a proposta funciona
- ele ainda nao prova que consegue operar com seguranca comercial e fluidez

O estado atual e bom para demonstracao tecnica e entrega parcial.

Ainda nao e bom para afirmar:

- que a conversa sempre pergunta a coisa certa
- que o ranking entrega a melhor peca com confianca
- que o tempo de resposta esta aceitavel para operacao real

O foco imediato deveria ser menos "ensinar mais casos para a IA" e mais "parar de errar com conviccao em casos comuns".
