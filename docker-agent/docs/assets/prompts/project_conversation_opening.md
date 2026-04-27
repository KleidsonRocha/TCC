Quero conversar sobre o projeto `docker-agent`.

Contexto base:
- o projeto e um servico FastAPI para atendimento inicial de autopecas
- ele recebe texto livre em `POST /respond`
- usa extracao deterministica + catalogo em Postgres + validacao com LLM via Ollama
- o backend decide entre `ask`, `search` e `handoff`
- a busca no ERP so acontece quando o criterio esta suficientemente valido

Arquitetura resumida:
- `app/`: runtime da API e regras de negocio
- `db/`: bootstrap consolidado e catalogo deterministico
- `docs/`: documentacao principal, backlog e evidencias
- `scripts/`: avaliacao, benchmark, treino e suporte operacional
- `trainer/`: ambiente separado para fine-tuning

Estado atual relevante:
- ja existe bateria real, datasets de avaliacao e benchmark
- ja existe fluxo de revisao, promocao e fine-tuning com LoRA/QLoRA
- o projeto prioriza corrigir regras, catalogo e gates antes de usar ML para mascarar falhas deterministicas

Ao responder, considere:
- preservar o objetivo do TCC
- manter a arquitetura hibrida atual
- evitar propostas que substituam regra de negocio por ML sem justificativa forte
- priorizar consistencia com `AGENTS.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md` e `docs/TODO.md`

Quero continuar a partir desse contexto.
