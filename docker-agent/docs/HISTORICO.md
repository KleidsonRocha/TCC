# Historico Consolidado Do Projeto

Consolidado em 14/09/2026 a partir dos relatorios antigos, do backlog legado e
dos relatos duplicados de problemas e solucoes. Estado atual em
[PROGRESS.md](PROGRESS.md), decisoes vigentes em [DECISIONS.md](DECISIONS.md)
e todo trabalho pendente em [TODO.md](TODO.md).

Os numeros abaixo pertencem as versoes e ambientes indicados. HTTP 200,
assertions estruturais e acerto comercial sao medidas diferentes. Resultados
historicos nao comprovam a qualidade da versao atual em producao.

## Marco E Abril: Baseline E Curadoria

| Data | Evidencia | Consequencia |
| --- | --- | --- |
| 25/03/2026 | Bateria real: 50 pedidos, 48 HTTP 200, 27 `request_info`, 17 `show_items`, 4 handoffs e 2 erros HTTP. Media 39,28 s; maximo 67,88 s. | Faltavam regras consistentes de familia, follow-up, ranking e tratamento de falhas. |
| 15/04/2026 | Primeira revisao: 76 interacoes pendentes em 47 conversas, 9 handoffs e quatro grupos de duplicidades exatas. | Revisao inicial era sugestao de curadoria; nao autorizava promocao automatica para treino. |
| 17/04/2026 | Comparacao de tres modelos base no MVP, golden set e bateria de 50 pedidos. `gemma3:12b` interrompido, com chamadas de 185–203 s. | Manter baseline mensuravel antes de treinar ou trocar o modelo. |

Comparativo de abril, anterior as correcoes deterministicas posteriores:

| Modelo | Decisao MVP | Casos aprovados no golden | Media do golden | Media da bateria real |
| --- | ---: | ---: | ---: | ---: |
| `qwen2.5:7b` | 35,0% | 100,0% | 33,50 s | 55,24 s |
| `qwen3:8b` | 15,0% | 100,0% | 45,24 s | 45,99 s |
| `llama3.1:8b` | 20,0% | 84,62% | 39,90 s | 43,57 s |

Os tres tiveram 48 respostas HTTP 200. O relatorio considerou Qwen3 candidato
de equilibrio, mantendo Qwen2.5 como baseline conservador; Llama perdeu em
campos faltantes e pergunta seguinte. A divergencia entre MVP e golden exige
avaliar cobertura e expectativas antes de interpretar percentuais.

## Julho A Setembro: Regras, Estado E Latencia

- **13/07:** bloqueio de `part_code` inventado, exemplificado por `FREIO-2010`;
  codigos exigem proveniencia. Ajustadas regras de eixo/lado de filtros no
  catalogo e bootstrap. Suite evoluiu de 136 para 148 testes.
- **14/07:** busca completa passou a usar `deterministic_bypass`, com latencia
  por etapa. Na mesma maquina, `radiador Gol 2010 1.0` caiu de 71,67 s para
  1,31 s; follow-up `1.0`, de 46,73 s para 0,93 s. Suite: 159 testes.
- **27/08:** `deterministic_ask` usa campos obrigatorios e opcoes do catalogo.
  Comparacao pareada de 50 casos, Qwen2.5 em CPU: chamadas LLM 31 -> 12;
  media total 23,15 -> 10,84 s; mediana 31,41 -> 0,74 s. Nos 19 casos
  transferidos, media 35,33 -> 0,72 s. P95 total 42,94 -> 43,90 s: a cauda
  da LLM continuou alta. Cinco respostas ganharam opcoes governadas de motor.
  Suite daquele bloco: 187 testes.
- **27/08:** `no_match` passou a preservar criterios e permitir nova tentativa,
  sem declarar incompatibilidade mecanica ou encaminhar automaticamente.
  Desambiguacao persiste candidatos/atributos e filtra respostas sucessivas.
- **27–28/08:** bateria estrutural ampliada para 135 cenarios/164 turnos, com
  27 cenarios exigindo revisao humana. Runner passou a excluir respostas
  futuras do contexto. Smoke omnichannel: 30 cenarios/65 turnos, todos HTTP
  200, zero falhas estruturais e zero vazamento temporal; mediana 36,4 s,
  media 28,9 s e P95 55,9 s. Foram 43 chamadas LLM, 12 perguntas
  deterministicas, 6 buscas com bypass e 4 desambiguacoes. Isso nao
  significava 100% de acerto semantico/comercial.
- **08/09:** revisao visual por conversa/turno, edicao multi-item, historico
  de revisoes e reabertura. Corrigidos lado para velas/aditivos e eixo para
  anti-chama. Estado continua no Redis do `docker-comm`; testes diretos na
  API precisam reenviar o estado retornado.
- **11/09:** follow-up `2008` preserva ano, sem virar modelo Peugeot 2008;
  direcao respeita o campo pendente. Coxins exigem posicao, nao eixo;
  pastilhas nao exigem motor como campo obrigatorio.

## Auditoria Especialista De 11/09/2026

Avaliacao anterior ao contrato ERP v2: **6/10 como prototipo de TCC e 4/10
para prontidao de producao**. Notas qualitativas de engenharia, nao metricas
estatisticas ou notas recalculadas apos as correcoes.

Evidencias: 261 testes automatizados; smoke estrutural 30/30 turnos; bateria
adicional exclusivamente automotiva com 15 cenarios/23 turnos, todos HTTP 200,
mas com erros funcionais. Conferidos 43 arquivos Python contra a imagem, sem
diferenca. A janela de logs mostrou 22 buscas `erp_postgres`, sem fallback.

| Prioridade original | Achado e reproducao | Situacao apos 14/09 |
| --- | --- | --- |
| P1 | `radiador Gol 2010 1.0` aceitava `AUD-REAL`, `AUD-GOLF`, `AUD-CROSS` e `AUD-CAP`: substring, anos agregados, atributos cruzados e acessorio. | Corrigido por identidade e aplicacao; somente `AUD-REAL` aceito no golden SQL. |
| P1 | `pastilha traseira ... nao dianteira` virou dianteira; `nao quero radiador, quero filtro` incluiu radiador. | Pendente: negacao antes do bypass. |
| P1 | `radiador Gol 2010 1.0 e radiador Corsa 2011 1.4` perdeu item e misturou veiculo/ano/motor. | Pendente: identidade e contexto por item. |
| P1 | Bandeja sem lado pesquisada; `esquerda` afetou item errado; codigo simulado `ZZ-12345` da LLM chegou a ferramenta. | Pendente: gate/proveniencia por item e follow-up. |
| P1 | Corrigir Gol para Corsa durante desambiguacao manteve candidatos antigos. | Pendente: invalidar candidatos ao mudar criterios. |
| P1 | `SearchPartsServiceUnavailableError` simulada virou HTTP 200 com `no_match_retry`. | Pendente: separar falha de ausencia de produto. |
| P1 | `/health` excedeu 3 s durante inferencia e respondeu em 24 ms depois. | Pendente: remover I/O bloqueante e isolar auditoria por requisicao. |
| P1 para exposicao | Revisao retornou 200 sem chave administrativa; portas publicadas em todas as interfaces. Firewall externo nao auditado. | Pendente: autenticacao e limites de acesso/entrada. |
| P2 | `zetec rocam` e `nao sei a motorizacao` repetiram pergunta; `4 velas NGK` nao reconhecido; descricao funcional fixou familia sem confirmar. | Pendente: motor textual, lexical e confirmacao de familia. |
| P2 | Benchmark aprovava campos extras incorretos; entrada exportada para treino omitia estado/regras do runtime. | Pendente: avaliacao e paridade treino/runtime. |

Outros casos: `Honda Gol` aceito sem confirmar conflito; codigo inexistente
recebeu ausencia sem produto inventado; radiador -> sem ar -> opcao 1
funcionou. LLM em CPU: mediana 40,78 s em nove amostras, entre 34,64 e
81,87 s. GPU nao resolve os erros de intencao ou concorrencia. Os criterios
de aceitacao dos achados abertos permanecem no [TODO](TODO.md).

## Correcao Da Busca Em 14/09/2026

Contrato passou a separar item e aplicacao. Modelo exato, ano individual,
fim aberto explicito e motor da propria aplicacao sao filtrados juntos.
Identidade de familia precede ranking; tampas, kits e mangueiras continuam
pesquisaveis por sua propria familia. Somente aplicacoes aprovadas fornecem
atributos de desambiguacao.

Validacao anterior a limpeza documental: 343 testes, incluindo 38 casos
automotivos nos SELECTs externos e apos COPY (76 verificacoes). Snapshot
exportado do banco quente em 14/09, 12:43 UTC: **52.798 itens e 1.776.907
aplicacoes**, UTF-8, dois CSVs gzip, manifesto e checksums. A exportacao
original consultou tabelas de origem pelos SELECTs do contrato; o exportador
atual consulta diretamente as views instaladas.

Quatro pedidos passaram pela API real com catalogo e fallback locais:
radiador Gol 2010 1.0 retornou quatro radiadores; tampa desse radiador retornou
`TC-7018`; coxim de amortecedor dianteiro EcoSport 2008 1.6 retornou cinco
coxins; radiador Golf 2010 1.6 retornou zero, sem substituir por Gol. Busca
local entre 19,92 e 48,50 ms; configuracao ERP + fallback teve 188,38 ms de
busca e 846,24 ms total no pedido de radiador. Sao amostras pontuais,
nao um novo benchmark de latencia.

Tabelas anteriores em `search_snapshot_backup_38555ef20e3c`; imagem anterior
com tag `docker-agent-docker-agent:before-erp-v2-20260914`. O usuario informou
a instalacao do SQL no banco quente. Implantacao na VPS permanece no backlog.

## Curadoria E Treinamento

Fila `pre_search_review_interaction` separada do dataset formal
(`pre_search_fine_tuning_dataset_header/record`) e das runs. Revisar, promover
e exportar continua obrigatorio antes do treino. Snapshots antigos com
pergunta/campos faltantes obsoletos em alvos `search` recebem normalizacao
documentada no metadata do exportador.

Export validado do `pre-search-ft-v1`: 122 exemplos de treino, 15 de validacao
e 15 de teste em UTF-8; 13 testes focados passaram. Auditoria de 11/09:
zero runs. Isso comprova preparacao do fluxo, sem comprovar ganho de adapter.
Teste retido, comparacao com baseline e promocao controlada seguem no backlog.

## Organizacao Dos Arquivos

Consolidados aqui: `PROBLEMAS_E_SOLUCOES.md`, `TODO_OLD.md`, historico de
`PROGRESS.md` e os sete arquivos de relatorios de marco, abril, agosto e
setembro. O prompt de abertura repetia README/AGENTS e foi removido.
Pendencias antigas continuam no TODO atual ou como hipoteses adiadas.

Datasets ativos e roteiro de validacao humana permanecem em
[assets/datasets](assets/datasets/README.md). Novos relatorios ficam em
`.tmp/eval/`; resultados interpretados entram nos documentos. Bootstrap local
em `db/init/pre_search_init.sql`. DDL do ERP e material operacional fora do
Git. O avaliador aceita copia local por `--integration-sql` para auditar
SELECTs de origem sem aplicar DDL no banco quente. Instrucoes em
[integracao ERP](guide/erp_search_integration.md).
