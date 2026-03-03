# Próximos Passos — Evolução do Sistema (docker-comm + docker-agent)

## 1. Integração com Motor de Busca Real

Substituir a `tool mock` atual (`search_parts`) por uma integração com um motor de busca real.

### 1.1 Decisão de Arquitetura
Avaliar e definir qual motor será utilizado:

- PostgreSQL (consulta direta com regras e ranking)
- Serviço dedicado de busca (ex.: reaproveitamento do motor atual como microserviço)
- Elastic/OpenSearch (caso seja necessário maior capacidade de relevância e fuzzy search)

### 1.2 Objetivo da Integração
A ferramenta de busca deve retornar:

- Lista de candidatos (`item_id`, `title`, `score`)
- Apenas itens elegíveis (ativos, conforme regras de negócio)
- Ranking determinístico

O `docker-agent` continuará responsável pela decisão, não pela busca em si.

---

## 2. Evolução do docker-agent com LLM (Camada de Inteligência)

Após a integração com o motor de busca real, iniciar a evolução do agente para incorporar um analisador baseado em LLM.

### 2.1 Papel do LLM (Pré-Busca)

O LLM deverá:

1. Receber a mensagem do usuário.
2. Interpretar o texto.
3. Extrair entidades relevantes (ex.: veículo, ano, motorização, lado, tipo de peça).
4. Determinar se as informações são suficientes para realizar a busca.
5. Caso não sejam suficientes:
   - Identificar quais dados estão ausentes.
   - Determinar a melhor pergunta a ser feita (baseada nos pilares de pesquisa).
   - Retornar `request_info`.

---

### 2.2 Execução da Busca

Se o LLM determinar que já há informações suficientes:

1. O `docker-agent` chama a tool de busca real.
2. Recebe a lista de candidatos.

---

### 2.3 Papel do LLM (Pós-Busca)

Após receber os resultados da busca, o mesmo LLM deverá:

1. Avaliar os candidatos retornados.
2. Determinar se já há um único item suficientemente claro para resposta.
3. Caso exista ambiguidade:
   - Identificar qual critério reduz melhor o conjunto (ex.: ano, motor, lado).
   - Formular a pergunta mais adequada para refinar.
4. Caso não haja resultados:
   - Sugerir coleta de mais dados ou handoff.

---

## 3. Fluxo Final Esperado

1. Mensagem entra no `docker-comm`.
2. `docker-comm` envia para `docker-agent`.
3. LLM (pré-busca) analisa e decide:
   - Perguntar mais dados, ou
   - Executar busca.
4. Busca é executada.
5. LLM (pós-busca) decide:
   - Responder com item final,
   - Mostrar opções,
   - Ou solicitar refinamento adicional.
6. Resposta estruturada retorna ao `docker-comm`.

---

## 4. Objetivo Estratégico

Separar claramente responsabilidades:

- Motor de busca → geração de candidatos.
- docker-agent → orquestração e decisão.
- LLM → interpretação e refinamento inteligente.
- docker-comm → transporte, sessão e integração com canais.

Essa evolução permitirá:

- Maior precisão na determinação do produto.
- Redução de ambiguidades.
- Melhor experiência conversacional.
- Base sólida para expansão futura (RAG, fine-tuning, novas tools).