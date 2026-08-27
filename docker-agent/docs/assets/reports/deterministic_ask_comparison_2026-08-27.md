# Comparacao Real Do `deterministic_ask` - 27/08/2026

## Objetivo

Validar se os criterios conservadores e a ativacao do caminho `deterministic_ask` melhoraram latencia sem piorar o comportamento funcional do `/respond`.

## Metodo

- mesma bateria real de 50 casos executada duas vezes contra a API e o catalogo Postgres reais
- baseline com `PRE_SEARCH_DETERMINISTIC_ASK_ENABLED=false`
- candidato com `PRE_SEARCH_DETERMINISTIC_ASK_ENABLED=true`
- mesmo modelo `qwen2.5:7b`, carregado no Ollama em `100% CPU`
- bypass de `search`, ERP, catalogo, modelo e demais configuracoes preservados
- comparacao por status, resultado observavel, handoff, `question_key`, criterios, `pending_slot`, opcoes, caminho e latencia
- suite completa executada em container Linux descartavel com a imagem oficial do projeto

## Resultado Consolidado

| Metrica | Baseline | `deterministic_ask` | Diferenca |
|---|---:|---:|---:|
| Casos | 50 | 50 | igual |
| Chamadas a LLM | 31 | 12 | `-19` (`-61,3%`) |
| Caminho `deterministic_ask` | 0 | 19 | `+19` |
| Latencia media total | 23.150,87 ms | 10.836,37 ms | `-53,19%` |
| Latencia p50 total | 31.410,35 ms | 741,96 ms | `-97,64%` |
| Latencia p95 total | 42.939,14 ms | 43.902,60 ms | `+2,24%` |
| Tempo acumulado dos 50 casos | 1.157.543,66 ms | 541.818,29 ms | `-615.725,37 ms` |
| Diferencas funcionais centrais | 0 | 0 | sem regressao observavel |

O p95 nao melhorou porque os 12 casos residuais continuam dependendo da LLM em CPU e apresentam variacao alta. O novo caminho reduziu a mediana e a media, mas nao resolve a cauda dos casos deliberadamente excluidos da politica conservadora.

## Casos Efetivamente Otimizados

Nos 19 casos que migraram de `llm` para `deterministic_ask`:

- media: `35.325,42 ms -> 721,21 ms`, reducao de aproximadamente `97,96%`
- p50: `33.549,86 ms -> 713,19 ms`
- p95: `40.035,85 ms -> 838,59 ms`
- maximo: `69.820,06 ms -> 933,72 ms`

Exemplos:

| Entrada | Pergunta | Antes | Depois | Reducao |
|---|---|---:|---:|---:|
| `radiador gol 2010` | `engine` | 30.330,40 ms | 699,52 ms | 97,69% |
| `bandeja ecosport 2008` | `side` | 31.340,10 ms | 796,88 ms | 97,46% |
| `quero uma peca` | `part_query` | 27.192,50 ms | 392,07 ms | 98,56% |
| `pastilha de freio gol 2010 1.0` | `position` | 69.820,06 ms | 933,72 ms | 98,66% |

## Qualidade

- nenhum dos 50 casos mudou de status, resultado central, handoff, `question_key`, criterios normalizados ou `pending_slot`
- cinco casos passaram a receber opcoes de motor vindas diretamente do catalogo, enquanto o baseline da LLM havia devolvido a pergunta sem opcoes
- as diferencas `Gol/GOL`, `Ecosport/ECOSPORT` e `Focus/FOCUS` sao apenas caixa da forma canonica do catalogo
- `rdiador`, `pstilhas` e `bndejas` usaram o novo caminho porque sao aliases literais versionados no catalogo; nao houve promocao de fuzzy isolado
- casos fora do catalogo, handoff e follow-ups com estado pendente continuaram na LLM
- os dois erros de validacao continuaram retornando HTTP `400`

## Limitacoes E Achados Paralelos

- o Ollama permaneceu em CPU; por isso os casos residuais ainda ficaram entre aproximadamente 32 e 70 segundos
- follow-ups complexos, motor textual e `no_match` continuam apresentando os problemas ja registrados na Prioridade 1
- o volume Postgres atual ainda possui `FILTRO DE COMBUSTIVEL -> needs_side=true`, apesar de o bootstrap versionado ja estar corrigido; o novo caminho preservou a mesma pergunta errada do baseline, portanto nao criou regressao, mas tornou mais evidente que regra stale no banco tambem sera executada mais rapidamente
- antes de beta, o catalogo do ambiente deve ser reconciliado com o bootstrap consolidado sem apagar dados dinamicos

## Testes Automatizados

- suite oficial no container Linux: `187 passed in 31.70s`
- suite focada do `deterministic_ask`: aprovada
- comparacao real: `100` chamadas ao endpoint, sendo `50` de baseline e `50` com a flag ligada

## Conclusao

As duas implementacoes melhoraram materialmente o fluxo alvo. A latencia dos casos elegiveis caiu cerca de 98%, a mediana global caiu 97,64%, cinco respostas ganharam opcoes governadas pelo catalogo e nenhuma regressao funcional central foi observada. A feature flag deve permanecer ligada. A proxima melhoria de latencia deve se concentrar nos casos residuais de LLM, depois de corrigir as pendencias multi-turno e reconciliar o catalogo ativo.
