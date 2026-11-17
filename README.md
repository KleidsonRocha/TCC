# TCC - Assistente De Atendimento Para Autopecas

Este repositorio contem a stack do TCC dividida em dois servicos principais:

- `docker-agent`: API FastAPI responsavel pela regra de negocio, catalogo deterministico, validacao com LLM via Ollama e integracao com banco.
- `docker-comm`: gateway FastAPI e interface Streamlit para conversa, historico curto no Redis e chamada ao `docker-agent`.

Este arquivo e o ponto de entrada para instalar e rodar tudo em outra maquina.

## Documentacao E Arquivos Versionados

- [Mapa da documentacao do agente](docker-agent/docs/README.md): guias atuais, decisoes, progresso e historico tecnico.
- [Guia do gateway](docker-comm/docs/guia_execucao_e_implementacao.md): execucao e integracao do canal.
- [Evidencias do artigo](evidencias/README.md): fontes das Tabelas 5 a 11, scripts, rubricas e relatorios arquivados para consulta pela banca.
- `.tmp/Documents/`: rascunhos e entregas locais; as evidencias citadas no artigo sao publicadas em `evidencias/`.

Codigo, testes, datasets de avaliacao, seeds e snapshot de contingencia fazem
parte do repositorio para permitir reproducao. Pesos de modelos, backups,
relatorios operacionais e analises substituidas ficam locais e ignorados pelo Git.
Os registros de pesquisa selecionados para sustentar as tabelas ficam versionados
em `evidencias/`, com manifesto SHA-256 e procedimento de conferencia.
O snapshot comprimido e versionado via Git LFS; preserve `.gitattributes`.

## Reprodução dos resultados

O código da ablação final de 26–27/10/2026 é o commit
`52e4d7460009d9635445c8ca69c604488b5dacef`. O commit que publica estas
evidências é posterior: ele não deve ser confundido com a versão executada.
A [conferência do código congelado](evidencias/VERSAO_EXPERIMENTAL.json)
compara 178 arquivos com esse commit; a única divergência é um TODO documental.
Código de execução e testes correspondem à versão experimental.

| Tabela do artigo | Experimento | Script de conferência | Arquivo de origem versionado |
|---|---|---|---|
| 5 | Antes/depois de `deterministic_ask`, 50 casos | [compare_deterministic_ask.py](evidencias/05_desempenho/compare_deterministic_ask.py) | [Baseline](evidencias/05_desempenho/deterministic_ask_baseline_50.json) e [candidato](evidencias/05_desempenho/deterministic_ask_enabled_50.json) |
| 6 | Ranking: 30 consultas positivas e protocolo de ausência | [evaluate_real_ranking.py](evidencias/04_ranking/evaluate_real_ranking.py) | [Execução de 29/09](evidencias/04_ranking/real_respond_battery_comm_20260929T125748400473Z.json), [anotações](evidencias/04_ranking/real_respond_ranking_annotations_v1.json), [execução pareada](evidencias/04_ranking/bateria_ranking_atual.json) e [relatório](evidencias/04_ranking/comparacao_ranking.md) |
| 7 | Comparação qualitativa com Elasticsearch, 05/10 | Não há reexecução automática disponível | [Registro do alcance e da lacuna documental](evidencias/06_elasticsearch/LEIA_ME.md); as saídas originais completas do Elasticsearch não foram localizadas |
| 8 | Base versus LoRA BF16, 19/10 | `aggregate.py` em [registros_20261019.zip](evidencias/03_fine_tuning/registros_20261019.zip) | Quatro `report.json` no mesmo ZIP e [comparison_summary.json](evidencias/03_fine_tuning/comparison_summary.json) |
| 9 | Triagem das 371 conversas por modelo, 19/10 | O mesmo `aggregate.py` da Tabela 8 | [comparison.md](evidencias/03_fine_tuning/comparison.md) e os mesmos registros, sem confundir triagem cadastral com acerto comercial |
| 10 | Ablação final D/H, três repetições, 26–27/10 | `tecnico/analysis/aggregate_results.py` em [01_tecnico.zip](evidencias/01_tecnico.zip) | `tecnico/runs/` (3.408 casos), `tecnico/summary.json`, protocolo, entradas e código congelado no mesmo ZIP |
| 11 | Três rubricas auxiliares dos 371 casos | [avaliar_371.py](evidencias/reproducao/rubricas/avaliar_371.py), [critérios](evidencias/reproducao/rubricas/criterios_371.py) e [conferidor portátil](evidencias/reproducao/conferir_resultados.py) | [02_rubricas.zip](evidencias/02_rubricas.zip): três `avaliacao_IA_*_V3.json`, `avaliacoes_371.csv`, chave A/B e [métricas](evidencias/rubricas/metricas_por_configuracao.json) |

Depois de clonar o GitHub ou o Forge, use Python 3.11 ou posterior. A conferência
das métricas arquivadas utiliza somente a biblioteca padrão, sem GPU, Docker,
credenciais ou ERP ativo:

```text
python -X utf8 evidencias/reproducao/conferir_resultados.py
python -X utf8 evidencias/reproducao/conferir_resultados.py --recalcular --saida .tmp/conferencia_artigo
```

O segundo comando exige uma pasta de saída nova e recalcula as Tabelas 5, 6,
8, 9 e 10, além de recontar as classificações da Tabela 11. Para também executar
novamente as regras semânticas originais dessa rubrica, use o snapshot experimental
de 19/10 já publicado em `evidencias/catalogo_20261019/`:

```text
python -X utf8 evidencias/reproducao/conferir_resultados.py --recalcular --rubricas --saida .tmp/conferencia_com_rubricas
```

Consulte o [índice e os limites de reprodução](evidencias/README.md), o
[adendo](evidencias/documentacao_recebida/RESPOSTAS_PARA_O_TCC.md) e a
[auditoria da revisão](evidencias/documentacao_recebida/AUDITORIA_DA_REVISAO.json).
As rubricas auxiliares não são notas individuais dos profissionais nem uma taxa
única de acerto da IA. Recalcular registros arquivados também é diferente de
reexecutar inferência e buscas.

**Fonte cadastral:** o snapshot experimental de 19/10 tem 52.798 produtos e
1.779.443 aplicações. Ele difere do snapshot de contingência de 14/09 no commit
(1.776.907 aplicações). O [manifesto experimental](evidencias/catalogo_20261019/manifest.json)
identifica a fonte usada na avaliação; o snapshot operacional não foi substituído.

O [workflow de espelhamento](.github/workflows/mirror-forgejo.yml) transfere
branches, tags e objetos LFS. A publicação só está confirmada após commit/push,
sucesso da Action e conferência destes arquivos e hashes no Forge URICER.

## Requisitos

Para rodar o projeto via Docker:

- Docker Desktop com Docker Compose
- WSL2 ativo no Windows
- virtualizacao habilitada na BIOS/UEFI
- Git, caso va clonar o repositorio
- internet no primeiro setup, para baixar imagens Docker, dependencias e modelo do Ollama
- aproximadamente 50 GB livres em disco

Nao e necessario instalar manualmente Python, PostgreSQL, Redis, Ollama, FastAPI ou Streamlit para o uso normal. Esses componentes sobem em containers.

## Estrutura

```text
TCC/
  docker-agent/
    docker-compose.yml
    Dockerfile
    README.md
    app/
    db/
    docs/
    scripts/
    trainer/

  docker-comm/
    docker-compose.yml
    Dockerfile
    README.md
    app/
    ui/
    docs/
```

## Instalacao Em Uma Nova Maquina

1. Instale o Docker Desktop.

2. No Windows, confirme que o Docker Desktop esta usando WSL2.

3. Clone ou copie este repositorio para a maquina:

```powershell
git clone <url-do-repositorio> TCC
cd TCC
```

Se o projeto foi entregue como pasta ou ZIP, apenas extraia e entre na pasta `TCC`.

4. Configure o `docker-agent`:

```powershell
cd docker-agent
Copy-Item .env.example .env
```

5. Suba o `docker-agent`, Postgres e Ollama:

```powershell
docker compose up -d --build
```

6. Baixe o modelo usado pelo Ollama:

```powershell
docker exec ollama ollama pull qwen2.5:7b
```

7. Configure o `docker-comm`:

```powershell
cd ..\docker-comm
Copy-Item .env.example .env
```

O `.env.example` ja vem preparado para o modo Docker Compose:

```env
AGENT_URL=http://docker-agent:8001/respond
REDIS_URL=redis://redis:6379/0
COMM_API_URL=http://docker-comm:8000
STREAMLIT_PORT=8501
```

8. Suba o `docker-comm`, Redis e interface Streamlit:

```powershell
docker compose up -d --build
```

## Acessos

Depois da subida, os principais enderecos sao:

- Interface Streamlit: `http://localhost:8501`
- API do gateway `docker-comm`: `http://localhost:8000`
- API do agent `docker-agent`: `http://localhost:8001`
- Ollama: `http://localhost:11434`
- Postgres do catalogo: `localhost:5433`
- Redis: `localhost:6379`

## Validacao Rapida

No `docker-agent`:

```powershell
cd D:\TCC\docker-agent
docker compose ps
curl http://localhost:8001/health
docker exec ollama ollama list
```

No `docker-comm`:

```powershell
cd D:\TCC\docker-comm
docker compose ps
curl http://localhost:8000/health
```

Tambem e possivel abrir a interface em:

```text
http://localhost:8501
```

## Derrubar A Stack

Para parar os containers mantendo os volumes:

```powershell
cd D:\TCC\docker-comm
docker compose down

cd D:\TCC\docker-agent
docker compose down
```

Para recriar banco, catalogo e volume do Ollama do zero:

```powershell
cd D:\TCC\docker-agent
docker compose down -v
docker compose up -d --build
docker exec ollama ollama pull qwen2.5:7b
```

Use `down -v` com cuidado, porque ele remove volumes locais do Docker daquele compose.

## Problemas Comuns

### Docker nao conecta ao engine

Abra o Docker Desktop e aguarde o status indicar que o engine esta rodando. Depois rode:

```powershell
docker version
docker compose version
```

### API responde que o validador esta indisponivel

Verifique se o modelo existe no Ollama:

```powershell
docker exec ollama ollama list
docker exec ollama ollama pull qwen2.5:7b
```

### `docker-comm` nao consegue chamar o `docker-agent`

Confirme que o `docker-agent` subiu primeiro e que o `.env` do `docker-comm` esta usando:

```env
AGENT_URL=http://docker-agent:8001/respond
```

Os dois composes usam a rede Docker `tcc-integration`. Por isso, suba primeiro o compose de `docker-agent`.

### Portas ocupadas

As portas usadas por padrao sao:

- `8001`: docker-agent
- `8000`: docker-comm
- `8501`: Streamlit
- `11434`: Ollama
- `5433`: Postgres do catalogo
- `6379`: Redis

Se alguma ja estiver em uso, ajuste o `docker-compose.yml` ou o `.env` correspondente.

## Desenvolvimento Local

O caminho recomendado para instalar em outra maquina e via Docker. Para desenvolvimento local sem Docker, consulte:

- `docker-agent/README.md`
- `docker-agent/docs/guide/runtime_and_bootstrap.md`
- `docker-agent/docs/guide/operational_commands.md`
- `docker-comm/README.md`
- `docker-comm/docs/guia_execucao_e_implementacao.md`

## Fine-Tuning

O servico `trainer` do `docker-agent` e opcional e so e usado para fine-tuning. Para esse fluxo, a maquina pode precisar de GPU NVIDIA, drivers atualizados e suporte de GPU no Docker/WSL.

Para apenas rodar o sistema e testar a interface, o `trainer` nao e necessario.
