# Analise da Estrutura e do Entregue Atual

Data da analise: 2026-03-13

## 1. Objetivo

Este documento consolida o que existe hoje no repositorio `D:\TCC`, comparando:

- a estrutura proposta nos documentos de arquitetura;
- a implementacao real encontrada em `docker-comm` e `docker-agent`;
- os pontos aderentes;
- os pontos que se afastam da proposta ou ainda estao em transicao;
- o que ja pode ser considerado entregue.

Observacao importante:
- esta leitura foi feita sobre o estado atual da workspace, incluindo alteracoes locais ainda nao commitadas no `docker-agent`.

## 2. Fontes analisadas

### Documentacao raiz
- `Documents/estado_atual.md`
- `Documents/proximos_passos.md`

### Documentacao do `docker-comm`
- `docker-comm/README.md`
- `docker-comm/docs/estrutura.md`
- `docker-comm/docs/esqueleto.md`
- `docker-comm/docs/guia_execucao_e_implementacao.md`

### Documentacao do `docker-agent`
- `docker-agent/README.md`
- `docker-agent/docs/estrutura.md`
- `docker-agent/docs/esqueleto.md`
- `docker-agent/docs/guia_execucao_e_implementacao.md`
- `docker-agent/docs/TODO.md`

### Implementacao validada
- `docker-comm/app/**`
- `docker-comm/tests/**`
- `docker-agent/app/**`
- `docker-agent/db/**`
- `docker-agent/scripts/**`
- `docker-agent/tests/**`

## 3. Resumo executivo

O repositorio esta bem organizado em dois servicos principais, com separacao clara de responsabilidades:

- `docker-comm` atua como gateway/orquestrador de transporte e contexto;
- `docker-agent` atua como motor de decisao de pre-search;
- a divisao em camadas (`api`, `core`, `ports`, `infra`) esta consistente nos dois servicos;
- a estrutura geral proposta foi respeitada.

O principal ponto de atencao e documental:

- os documentos da raiz (`Documents/estado_atual.md` e `Documents/proximos_passos.md`) estao atrasados em relacao ao codigo atual;
- eles ainda descrevem o `docker-agent` como deterministico e sem LLM, mas a implementacao atual ja possui LLM, extracao deterministica, catalogo em Postgres e score/gate de decisao.

Em termos de produto, o maior gap entre proposta e entrega atual ainda e:

- a busca real de pecas nao foi implementada no fluxo principal;
- `search_parts` continua mockado, embora o pre-search ja esteja mais avancado.

## 4. Estrutura atual consolidada

```text
TCC/
  Documents/
    documentacao macro do projeto
  docker-comm/
    gateway FastAPI + Redis + cliente HTTP do agent
  docker-agent/
    agent FastAPI + LLM pre-search + catalogo Postgres + busca mock
```

### 4.1 `docker-comm`

Estrutura real aderente ao desenho:

- `app/api`: rotas, dependencias e schemas
- `app/core/domain`: regras e modelos
- `app/core/usecases`: fluxo principal
- `app/core/ports`: contratos
- `app/infra`: Redis, HTTP client e logger
- `tests`: testes do endpoint e regras
- `Dockerfile` e `docker-compose.yml`

### 4.2 `docker-agent`

Estrutura real aderente ao desenho, com evolucao adicional:

- `app/api`: rotas e contrato v1.0
- `app/core/domain`: modelos, regras e objetos de pre-search
- `app/core/usecases`: orquestracao do `/respond`
- `app/core/ports`: `tools` e `pre_search_validator`
- `app/infra`: validador LLM, extrator deterministico, provider do catalogo e mock de busca
- `db/init`: schema e carga inicial do catalogo
- `scripts`: importacao de CSV e avaliacao do pre-search
- `tests`: testes de regras e endpoint

## 5. O que esta condizente com a estrutura proposta

## 5.1 Nivel de arquitetura

- Separacao em servicos independentes (`docker-comm` e `docker-agent`).
- Separacao de responsabilidades entre transporte/contexto e decisao.
- Contrato tecnico versionado (`schema_version = "1.0"`).
- Containerizacao presente nos dois servicos.
- Estrutura em camadas consistente e facil de evoluir.

## 5.2 `docker-comm`

- Recebe mensagens por HTTP em `POST /test/send`.
- Normaliza o payload para o contrato do agent.
- Mantem historico curto no Redis.
- Faz retry minimo e tratamento de timeout/502/503 na chamada ao agent.
- Aplica regra de `branch_id` default.
- Faz namespacing interno por `source:conversation_id`.
- Retorna resposta simplificada para o chamador.
- Possui logs estruturados e chave opcional por `X-API-Key`.
- Possui testes automatizados cobrindo regras basicas e endpoint.

Conclusao:
- o `docker-comm` esta alinhado com o que os documentos prometem para a fase atual.

## 5.3 `docker-agent`

- Expoe `GET /health` e `POST /respond`.
- Valida contrato e `message.text`.
- Mantem orquestracao centralizada em `ProcessAgentRequestUseCase`.
- Usa porta de abstracao para ferramentas (`ToolsPort`).
- Usa porta de abstracao para validacao de pre-search (`PreSearchValidatorPort`).
- Registra `tool_trace`, `confidence`, `actions` e `handoff`.
- Possui testes cobrindo fluxo principal e regras.

Conclusao:
- a base arquitetural do `docker-agent` tambem esta alinhada com a proposta.

## 6. O que evoluiu alem do documento base

O codigo atual do `docker-agent` ja avancou alem do que esta descrito em `Documents/estado_atual.md`:

- existe `LLMPreSearchValidator` em producao;
- existe `DictionaryPreSearchExtractor`;
- existe catalogo operacional em Postgres;
- existe modo strict de catalogo (`fail fast` no startup);
- existe score configuravel para decidir `search` vs `ask`;
- existem scripts de carga por CSV e avaliacao do MVP;
- o compose do agent ja sobe `ollama` e `presearch-db`.

Conclusao:
- a implementacao atual esta mais proxima de uma fase intermediaria entre o "v0.1 deterministico" e a "arquitetura alvo" do que os documentos macro deixam transparecer.

## 7. O que foge da proposta ou ainda esta incompleto

## 7.1 Divergencia documental

Os arquivos da raiz estao defasados:

- `Documents/estado_atual.md` descreve o agent como "deterministico (sem LLM)";
- `Documents/proximos_passos.md` trata a camada de LLM como proximo passo;
- isso ja nao representa o estado real do `docker-agent`.

Impacto:
- quem ler apenas a documentacao raiz tera uma visao antiga do projeto.

## 7.2 Busca real ainda nao entrou no fluxo principal

O maior item ainda pendente frente a arquitetura alvo e:

- `search_parts` continua mockado em `docker-agent/app/infra/tools_mock.py`;
- nao ha integracao real com ERP, base oficial, PostgreSQL de catalogo de pecas ou motor de busca dedicado;
- o pos-busca ainda depende do retorno simplificado do mock.

Impacto:
- o sistema esta forte em pre-search, mas ainda nao fecha a proposta completa de determinacao real da peca.

## 7.3 Auditoria persistente no `docker-comm` esta apenas preparada

Existe a porta:

- `docker-comm/app/core/ports/audit_repo.py`

Mas nao existe:

- implementacao concreta;
- injecao no fluxo principal;
- persistencia de auditoria alem dos logs.

Impacto:
- a arquitetura ja preve esse ponto, mas ele ainda nao esta entregue de fato.

## 7.4 Artefatos locais misturados na arvore

Foram encontrados artefatos de ambiente e execucao dentro do projeto:

- `docker-comm/.venvpy`
- `docker-agent/.tmp`
- `.pytest_cache`
- `__pycache__`

Impacto:
- isso polui a leitura da estrutura;
- aumenta o risco de confundir "codigo entregue" com "estado local de maquina";
- no caso atual, tambem dificultou a validacao de testes.

## 7.5 Ambiente local de testes esta inconsistente

Tentativa de validacao automatizada:

- `pytest -q` falhou porque `pytest` nao esta no Python global;
- o reaproveitamento da `.venvpy` tambem falhou porque ela aponta para um Python 3.12 inexistente;
- ao tentar carregar os pacotes da `.venvpy` no Python 3.14 atual, houve erro binario de `pydantic_core`.

Conclusao:
- os testes existem e a intencao de cobertura esta clara, mas a validacao local nao esta reproduzivel neste estado de ambiente.

## 8. O que ja pode ser considerado entregue

## 8.1 Entregue no `docker-comm`

- API FastAPI funcional com `health` e `test/send`;
- composicao limpa de dependencias;
- cliente HTTP resiliente para o agent;
- persistencia de contexto curto em Redis;
- regras de validacao e fallback operacional;
- suporte a `source` e namespacing interno;
- logs estruturados;
- configuracao por ambiente;
- conteinerizacao;
- testes iniciais automatizados.

## 8.2 Entregue no `docker-agent`

- API FastAPI funcional com `health` e `respond`;
- contrato v1.0 com resposta estruturada;
- validacao de pre-search com LLM;
- extracao deterministica baseada em catalogo;
- merge entre seed deterministica e saida da LLM;
- fallback quando a saida da LLM vem invalida;
- catalogo em Postgres como fonte unica;
- bootstrap por SQL e suporte a carga por CSV;
- score de decisao configuravel;
- scripts auxiliares de importacao e avaliacao;
- conteinerizacao com `ollama` e `presearch-db`;
- testes iniciais automatizados.

## 8.3 Entregue no nivel de solucao

- separacao entre gateway e agent;
- contrato de integracao entre servicos;
- caminho claro para evolucao incremental;
- base pronta para trocar a busca mock por busca real sem reestruturar tudo.

## 9. Leitura final por maturidade

### Ja esta solido

- organizacao da solucao em servicos;
- desenho das camadas internas;
- fluxo de transporte e contexto no `docker-comm`;
- pre-search no `docker-agent`;
- base documental dentro de cada servico.

### Ainda esta em transicao

- alinhamento da documentacao macro com a implementacao atual;
- reproducibilidade do ambiente de testes local;
- limpeza de artefatos de ambiente da arvore do projeto.

### Principal lacuna funcional

- integracao da busca real de pecas no lugar do mock.

## 10. Recomendacao objetiva

Prioridade sugerida para consolidar o que ja foi entregue:

1. Atualizar `Documents/estado_atual.md` e `Documents/proximos_passos.md` para refletir o estado atual do `docker-agent`.
2. Fechar a troca de `search_parts` mock por uma integracao real.
3. Padronizar o ambiente de testes local para que `pytest` rode sem dependencia de ambientes quebrados.
4. Limpar ou isolar artefatos locais da arvore do projeto.
5. Decidir se `audit_repo` sera implementado agora ou removido da narrativa de entrega atual.

## 11. Conclusao

O projeto ja tem uma base tecnica consistente e bem melhor estruturada do que um MVP improvisado.

Hoje, o que voce tem entregue nao e apenas um esqueleto:

- o `docker-comm` esta funcional e coerente com a proposta;
- o `docker-agent` ja entrou em uma fase mais avancada de pre-search com LLM e catalogo em banco;
- a maior diferenca entre "proposta" e "entrega completa" esta concentrada na ausencia da busca real de pecas e no atraso da documentacao macro.

Em outras palavras:
- a estrutura proposta foi majoritariamente respeitada;
- parte do sistema ja evoluiu alem do que a documentacao raiz diz;
- o principal passo para transformar essa entrega em uma versao mais fechada e produtizavel e substituir o mock de busca por integracao real e atualizar a documentacao central.
