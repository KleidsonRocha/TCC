# Revisão ampliada dos 371 casos — versão 3

**Revisão exploratória assistida por IA: três perspectivas do mesmo modelo/contexto, sem independência e sem revisão humana. O script aplica julgamentos semânticos explícitos e verificações cadastrais; não executa três modelos nem o chatbot.**

## Entrega e fonte corrigida

Esta revisão cobre os 371 casos (347 pedidos textualmente distintos) e as 742 saídas D/H da primeira repetição. As três perspectivas produzem 2.226 julgamentos de saída e respostas aos 21 campos da ficha por caso/saída. Há 337 referências históricas e 34 casos sem referência. A classificação indeterminada é uma resposta válida, não foi substituída por acerto/erro inventado.

Foi usado o snapshot de **19/10/2026** contido em `tecnico/inputs/source_snapshot`: **52.798 produtos e 1.779.443 aplicações**. Seus hashes e contagens foram conferidos. O CSV enviado separadamente antes era exportação de 14/09/2026 com 1.776.907 aplicações; tinha 2.536 vínculos a menos. Portanto a ressalva de divergência temporal global da versão 2 foi resolvida nesta versão usando a fonte efetiva do ensaio, sem apagar o histórico anterior.

**D** é a arquitetura determinística existente com encaminhamento conservador no ponto residual. **H** é a mesma arquitetura com Qwen2.5:7b residual e validações existentes. A chave `analyst_key.json` foi usada para converter A/B em D/H. **Esta bateria não compara modelo base versus fine-tuning.** D também não é uma implementação ideal ou exaustiva de todas as alternativas determinísticas possíveis.

## Metodologia efetivamente realizada

1. Conferência dos hashes e leitura dos CSV principais do snapshot correto; conservação dos arquivos originais.
2. Interpretação explícita dos 371 pedidos por função/composição e dados presentes. O gabarito está em `gabarito_exploratorio_371.json`; as anotações e regras de pontuação estão nos scripts e em `criterios_371.py`/`criterios_prioritarios.json`.
3. Verificação das referências e dos códigos retornados contra todas as suas aplicações no snapshot. Foram examinados 627 produtos referenciados/retornados ou selecionados para novos cenários, com 51.615 vínculos. A varredura do arquivo completo não significa que 1,77 milhão de linhas receberam interpretação humana individual.
4. Para sustentar um candidato, modelo, ano, motor e versão conhecida precisam ocorrer no **mesmo vínculo**. Identidade/composição e oposição explícita de lado/posição são verificadas separadamente; não se combinam veículo de uma linha e motor de outra. Dados omitidos não são completados por suposição.
5. Três perspectivas são aplicadas sequencialmente, por rubricas explícitas: balcão (perguntas/continuidade), aplicação (identidade/evidência/contenção de risco) e auditoria (fidelidade/rastreabilidade). O processo foi assistido por IA e materializado por scripts, **não foram três chamadas isoladas de LLM ou três profissionais independentes**.
6. Cada saída recebe adequada, parcial, inadequada ou indeterminada. Encaminhar pode ser seguro e adequado sob contenção de risco e parcial em autonomia. Um Top-1 sustentado não torna toda a lista correta. Parcial não entra na taxa estrita de adequação.
7. A chave foi aplicada à agregação e os desacordos preservados. A síntese só mantém uma classe quando unânime; divergência com indeterminado fica indeterminada, demais divergências ficam parciais. Isso é regra de apresentação, não adjudicação humana.
8. Os 3.408 registros técnicos arquivados foram recontados; somas de latência, chamadas, resultados e assinaturas das três repetições foram conferidos, sem nova execução do agente.

O contexto já continha respostas anteriores. **Não houve cegamento, pré-registro prospectivo ou independência entre personas.** Os hashes preservam os bytes desta entrega daqui em diante. Regras/aliases do próprio sistema não foram usados como verdade comercial independente; servem para diagnóstico. Não houve consulta a fabricante/ERP atual, nem demonstração de preço, estoque ou encaixe físico.

## Resultado por perspectiva e configuração

Cada linha tem 371 saídas. Os critérios da versão 3 incluem a fonte correta, cobertura ampliada e verificações de composição/lado por candidato; as contagens antigas da versão 2 não devem ser comparadas como se apenas o tamanho da amostra tivesse mudado.

|Perspectiva|Configuração|Adequadas|Parciais|Inadequadas|Indeterminadas|
|---|---|---:|---:|---:|---:|
|IA_BALCAO_V3|D|103|127|141|0|
|IA_BALCAO_V3|H|106|115|150|0|
|IA_APLICACAO_V3|D|122|135|29|85|
|IA_APLICACAO_V3|H|119|131|34|87|
|IA_AUDITORIA_V3|D|103|125|143|0|
|IA_AUDITORIA_V3|H|106|113|152|0|

Adequação por perspectiva não é precisão comercial validada. Por exemplo, uma pergunta genérica de eixo para uma peça elétrica pode ser inadequada em diálogo/auditoria, enquanto um encaminhamento que evita recomendar peça pode conter o risco de aplicação. Candidatos que dependem de medida de retífica, sistema, conector ou composição permanecem parciais/indeterminados.

Os recortes de 60 prioritários, 311 adicionais e 371 totais estão separados em `metricas_por_configuracao.json`. A síntese por todos os 24 grupos está em `categorias_por_grupo.csv`; a tabela de 2.226 linhas está em `avaliacoes_371.csv`. Nenhum desses denominadores foi multiplicado pelas três repetições como se fossem novos clientes.

## Contribuição incremental observada de H

Em cada repetição, **326/371 conversas foram idênticas**, 45 casos acionaram o modelo em H (12,1%), e H apresentou produtos em sete IDs nos quais D não apresentou. Esses sete IDs correspondem a seis pedidos distintos, pois AV-093 e AV-203 repetem o mesmo pedido.

|Caso|Top-1 cadastral H|Códigos retornados H|Balcão / Aplicação / Auditoria|
|---|---|---|---|
|AV-028|compatible|CB/49-CPA|Inadequada / Inadequada / Inadequada|
|AV-093|compatible|7130071100|Adequada / Adequada / Adequada|
|AV-296|compatible|CB/41 / CB/40|Parcial / Parcial / Parcial|
|AV-152|undetermined|YM245841|Parcial / Indeterminada / Parcial|
|AV-312|compatible|COR-78654|Adequada / Adequada / Adequada|
|AV-194|undetermined|AL-1259 / NJH09-204D / AL-1204|Parcial / Indeterminada / Parcial|
|AV-203|compatible|7130071100|Adequada / Adequada / Adequada|

Há cinco Top-1 sustentados cadastralmente e dois indeterminados entre esses sete IDs. Isso não significa sete sucessos comerciais: AV-028 oferece a sapata com lona, mas desmembra a composição em dois pedidos; AV-296 tem o primeiro código sustentado, mas o segundo candidato não foi aprovado. AV-152/194 permanecem pendentes de conferir período/composição. AV-093/203 e AV-312 apresentam conduções adequadas pelas rubricas, com AV-093/203 sendo duplicata textual.

Assim, os registros sustentam aumento de autonomia/retorno em um subconjunto e também mostram custo de latência e falhas residuais. Não sustentam superioridade comercial geral do híbrido nem ganho atribuível a fine-tuning.

## Auditoria técnica das três repetições

Foram conferidos **3.408 registros**, em 18 combinações de conjunto/repetição/configuração, sem divergências nas contagens e somas recalculadas. Os **3.716 arquivos do manifesto** conferem em tamanho/SHA-256. O manifesto de congelamento também cita um cache `.pyc` não incluído no pacote; ele foi registrado como bytecode ausente, não como código-fonte verificado. Os arquivos-fonte presentes conferem. Não foi ocultada essa omissão.

Os XMLs arquivados registram **604 testes do agente e 33 do gateway**, sem falhas/erros/skips. São evidências da execução anterior, não testes executados por mim nesta revisão. As 294 chamadas de inferência registradas estão em H; D tem zero. As conversas permaneceram iguais nas três repetições, conforme assinaturas recalculadas, embora os tempos variassem.

|Repetição|Configuração|Com produtos|Com handoff|Paradas por repetição de pergunta|Chamadas LLM|Média por caso (s)|P95 por caso (s)|
|---|---|---:|---:|---:|---:|---:|---:|
|1|D|165|176|5|0|2.163|4.096|
|1|H|172|159|10|57|10.299|56.115|
|2|D|165|176|5|0|2.138|4.143|
|2|H|172|159|10|57|8.524|35.274|
|3|D|165|176|5|0|2.154|4.122|
|3|H|172|159|10|57|8.452|35.026|

Nos 170 cenários estruturais, os checks arquivados/recontados passam em 163 casos para D e 164 para H em cada repetição. Nos 27 golden, os checks de campos originais passam em 22 para D e 24 para H. São checks de expectativa, não gabarito comercial independente. A análise de sobreposição/independência original continua separada desses números; esta entrega não transforma exemplos de treino em testes independentes.

## Lacunas de recuperação sustentadas

São 12 ocorrências em 8 IDs de caso, com duplicatas preservadas. O caso da flange para F-1000 4.9 aparece em AV-243 e AV-361 com o mesmo pedido. Há sete pedidos distintos nesse conjunto de oito IDs.

|Caso|Configuração|Código de evidência|Application ID|
|---|---|---|---|
|AV-069|H|COR-741876|99001914453206|
|AV-073|H|CBV144.525|99000892044884|
|AV-101|H|KT-20252|99001913896761|
|AV-101|D|KT-20252|99001913896761|
|AV-108|H|KT-50072|99001913903564|
|AV-149|D|YM612006|99001912871051|
|AV-149|H|YM612006|99001912871051|
|AV-243|H|KT-20252|99001913967564|
|AV-243|D|KT-20252|99001913967564|
|AV-298|H|COR-400229|99000987754142|
|AV-361|H|KT-20252|99001913967564|
|AV-361|D|KT-20252|99001913967564|

O escopo é recuperação **cadastral**: mesmo componente e vínculo que satisfaz modelo/ano/motor/versão conhecida. No pedido de flange, os critérios observados usam “semi eixo”, perdendo a identidade principal de flange; o vazio não comprova inexistência. Ainda assim, apontar esse sintoma não equivale a provar por contrafactual qual alteração no mecanismo recuperaria a peça. A causa interna final e a montagem física não foram adjudicadas.

Não foram promovidos a falso negativo pedidos genéricos cuja referência é kit, acessório ou outro componente. Por exemplo, kit com batente não comprova batente avulso; vareta não comprova cabeçote; maçaneta não comprova cabo do capô; pinhão não comprova cabo do velocímetro.

## Dez novos cenários

`dez_novos_casos_sinteticos.json` contém dez cenários com frase, contexto, complementações quando cabíveis, ação esperada e evidência do catálogo. Os identificadores de produtos são reais do snapshot, exceto o código inexistente usado em controle de consulta literal. Há casos completos, ambiguidade, correção, kit versus avulso, dado desconhecido, dimensão, volume/quantidade e ausência de referência exata.

O único caso de ausência confirmada restringe a conclusão ao identificador literal inexistente nos 52.798 registros; não afirma que uma peça funcionalmente equivalente não existe. Os dez casos são **sintéticos, gerados após exposição à bateria, não independentes e ainda não executados no agente**. Não são relatos de clientes reais. O hash preserva este gabarito para uma execução futura; não cria independência retroativa. O conjunto não entra nos denominadores 371/742.

## O que continua pendente

- Duas revisões de profissionais reais, independentes, com informação sobre vínculo e domínio.
- Adjudicação humana dos desacordos e conflitos de descrição/aplicação, sem apagar os originais.
- Dez pedidos reais anonimizados com evidências e gabarito congelados antes de testar.
- Executar os novos casos em ambiente isolado, preservando saídas e versões. Nenhuma execução nova do agente foi feita aqui.
- Para afirmar encaixe/equivalência, confirmar catálogo técnico/dimensões e configuração instalada onde o snapshot é conflitante.

## Uso acadêmico e reprodução

Redação fiel: “Foi realizada revisão exploratória assistida por IA dos 371 casos da bateria, sob três perspectivas dependentes de julgamento, fundamentada no snapshot de 19/10/2026. Foram preservadas avaliações parciais, indeterminadas e discordantes. A análise foi complementada por recontagem dos registros técnicos e não substituiu revisão comercial humana.”

Extraia o pacote e abra `RESULTADOS_371.html`. Para importar respostas na ficha original, use um dos três JSON `avaliacao_IA_*_V3.json`. Para reproduzir a parte computacional: `python reproducao/reproduzir.py /caminho/avaliacao_final_completa.zip`. É necessário Python 3.11+ e o ZIP original; o script usa apenas biblioteca padrão, cria diretório temporário separado e não chama rede, Docker, banco ou LLM. Ele reaplica os julgamentos registrados e refaz contagens/vínculos; não produz uma nova opinião independente.
