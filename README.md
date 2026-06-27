# TCC - Assistente De Atendimento Para Autopecas

Este repositorio contem a stack do TCC dividida em dois servicos principais:

- `docker-agent`: API FastAPI responsavel pela regra de negocio, catalogo deterministico, validacao com LLM via Ollama e integracao com banco.
- `docker-comm`: gateway FastAPI e interface Streamlit para conversa, historico curto no Redis e chamada ao `docker-agent`.

Este arquivo e o ponto de entrada para instalar e rodar tudo em outra maquina.

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
