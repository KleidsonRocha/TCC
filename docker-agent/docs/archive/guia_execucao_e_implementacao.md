# Guia de Execucao e Implementacao - docker-agent

## 1. O que esta implementado
- Validador de pre-busca baseado em LLM.
- Extracao deterministica de slots com catalogo em banco.
- Catalogo de negocio no Postgres (`dominio + aliases`).
- `search_parts` ainda mock (fase atual).

## 2. Pre-requisitos
- Docker Desktop com engine ativo.
- `docker-comm` apontando para `AGENT_URL=http://docker-agent:8001/respond` quando ambos em Docker.

## 3. Subir stack
```powershell
cd d:\TCC\docker-agent
docker compose up -d --build
```

Servicos esperados:
- `docker-agent` em `:8001`
- `ollama` em `:11434`
- `presearch-db` em `:5433`

## 4. Variaveis importantes
- `CATALOG_DB_ENABLED=true`
- `CATALOG_DB_HOST=presearch-db`
- `CATALOG_DB_PORT=5432`
- `CATALOG_DB_NAME=presearch`
- `CATALOG_DB_USER=presearch`
- `CATALOG_DB_PASSWORD=presearch`
- `LLM_BASE_URL=http://ollama:11434`
- `LLM_MODEL=qwen2.5:7b`

## 5. Seed e rebootstrap
Primeiro bootstrap (volume novo):
- `db/init/001_pre_search_catalog.sql` roda automaticamente.

Este projeto opera sem migrations.  
Se houve alteracao de schema, recrie o volume para reaplicar o `init`:

```powershell
docker compose down -v
docker compose up -d --build
```

Bootstrap automatico por CSV no nascimento da base:
- coloque os arquivos reais em `db/init/csv/`:
  - `grupo.csv`
  - `subgrupo.csv`
  - `pre_search_part_rule.csv`
  - `vehicle_brand.csv`
  - `vehicle_model.csv`
  - `engine_option.csv`
- suba com volume novo; o `001_pre_search_catalog.sql` carrega tudo sozinho.

Carga dos CSVs de dominio:
```powershell
python scripts/import_pre_search_catalog_csv.py `
  --grupo-csv "C:\Users\Desktop\Downloads\entregavel\grupo.csv" `
  --subgrupo-csv "C:\Users\Desktop\Downloads\entregavel\subgrupo.csv" `
  --part-rule-csv "C:\Users\Desktop\Downloads\entregavel\pre_search_part_rule.csv" `
  --vehicle-brand-csv "C:\Users\Desktop\Downloads\entregavel\vehicle_brand.csv" `
  --vehicle-model-csv "C:\Users\Desktop\Downloads\entregavel\vehicle_model.csv" `
  --engine-option-csv "C:\Users\Desktop\Downloads\entregavel\engine_option.csv" `
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Alternativa com CSV versionado no repo:
```powershell
python scripts/import_pre_search_catalog_csv.py `
  --grupo-csv "db/init/csv/grupo.csv" `
  --subgrupo-csv "db/init/csv/subgrupo.csv" `
  --part-rule-csv "db/init/csv/pre_search_part_rule.csv" `
  --vehicle-brand-csv "db/init/csv/vehicle_brand.csv" `
  --vehicle-model-csv "db/init/csv/vehicle_model.csv" `
  --engine-option-csv "db/init/csv/engine_option.csv" `
  --db-host localhost --db-port 5433 --db-name presearch --db-user presearch --db-password presearch
```

Notas:
- `pre_search_part_rule.csv` e `;` (nao `,`).
- `cd_subgrupo` repete entre grupos; `pre_search_part_rule.csv` deve ter `cd_grupo` + `part_type_id` (ou `cd_subgrupo`) em todas as linhas.
- `vehicle_model.csv` sem marca por linha entra em `--default-model-brand` (padrao `SEM_MARCA_MAPEADA`).
- Opcional: mantenha os CSVs em `db/init/csv/` para padronizar o fluxo do time.

## 6. Checks rapidos
Health:
```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8001/health"
```

Logs de carga de catalogo:
- procurar `pre_search_catalog_db_loaded` no `docker-agent`.

## 7. Fluxo do /respond (resumo)
1. valida contrato.
2. valida pre-search (`decision`, `criteria`, `missing_fields`, `next_question`).
3. `ask` -> retorna pergunta no mesmo output da 1a chamada da LLM (sem 2a chamada de reparo).
4. `search` -> chama `search_parts` mock.
5. monta `handoff`, `confidence`, `tool_trace`.

## 8. Campos de criteria aceitos
- `part_query`, `part_code`, `vehicle_brand`, `vehicle_model`, `vehicle_year`, `engine`, `side`, `position`, `axle`, `variant`, `quantity`.

## 8.1 Score de decisao (configuravel no banco)
Agora o pre-search usa gate de pontuacao para autorizar `search`:
- pesos por criterio em `pre_search_criteria_weight`
- limiar minimo em `pre_search_decision_policy.min_score_to_search`

Regras:
- com `part_code` valido: segue para `search` (atalho).
- sem `part_code`: se score < `min_score_to_search`, o fluxo vira `ask`.
- `vehicle_brand` so pontua quando vier explicita no texto/contexto (nao quando for apenas inferida por modelo).
- regras obrigatorias por tipo de peca continuam valendo (`needs_side`, `needs_engine`, etc.).

Consultas uteis:
```sql
SELECT criterion_key, weight, is_active
FROM pre_search_criteria_weight
ORDER BY weight DESC, criterion_key;

SELECT min_score_to_search
FROM pre_search_decision_policy
WHERE id = 1;
```

Exemplo de ajuste de pesos:
```sql
UPDATE pre_search_criteria_weight
SET weight = 55, updated_at = NOW(), updated_by = 'manual'
WHERE criterion_key = 'part_query';

UPDATE pre_search_criteria_weight
SET weight = 25, updated_at = NOW(), updated_by = 'manual'
WHERE criterion_key = 'vehicle_year';
```

Exemplo para deixar o agente mais critico (mais `ask`):
```sql
UPDATE pre_search_decision_policy
SET min_score_to_search = 85, updated_at = NOW(), updated_by = 'manual'
WHERE id = 1;
```

## 9. Observacoes de operacao
- Catalogo esta em modo strict: se DB/schema obrigatorio estiver ausente, startup falha.
- Isso e intencional para manter o banco como fonte unica da verdade.
