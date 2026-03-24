# Leitura Do Repositorio

Este guia existe para facilitar a leitura do `docker-agent` como repositorio de TCC.

## O Que E Nucleo Do Projeto

- `app/`
  Runtime da API, regras de negocio e integracoes.
- `db/`
  Schema consolidado e seeds do catalogo deterministico.
- `tests/`
  Evidencia automatizada do comportamento esperado.

Essas tres areas formam o nucleo tecnico principal.

## O Que E Apoio Experimental

- `scripts/`
  Automacao de carga, benchmark, avaliacao e treino.
- `trainer/`
  Ambiente de treino separado do runtime.
- `docs/assets/`
  Datasets e artefatos auxiliares.

Essas areas apoiam reproducao, medicao e evolucao do projeto.

## O Que E Material Historico

- `docs/archive/`

Esse diretorio deve ser lido apenas como contexto historico, nao como especificacao atual.

## Ordem Recomendada Para Banca

1. `README.md`
   Visao geral do problema atacado, do escopo e de como o repositorio esta dividido.
2. `docs/guide/pre_search_runtime_flow.md`
   Explica o caminho principal do texto livre ate `ask`, `search` ou `handoff`.
3. `docs/guide/runtime_and_bootstrap.md`
   Mostra como o ambiente sobe e como o catalogo e carregado.
4. `tests/`
   Demonstra os comportamentos protegidos por validacao automatizada.
5. `docs/TODO.md`
   Mostra o que ainda esta em aberto e como o trabalho continua.

## Como Interpretar O Projeto

- o `catalogo deterministico` e a base de reconhecimento lexical
- a `LLM` atua como validador e orquestrador, nao como decisor isolado
- a `busca no ERP` so acontece depois do gate de score e campos obrigatorios
- `fuzzy` foi introduzido como fallback controlado, nao como mecanismo principal

## O Que Nao Deve Ser Confundido Com Entrega Final

- `__pycache__/`, `.pytest_cache/` e `.tmp/` sao artefatos locais
- `docs/archive/` nao representa a arquitetura atual
- scripts de treino e benchmark nao fazem parte do runtime minimo da API
