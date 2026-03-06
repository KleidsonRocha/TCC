# Documento de Estado Atual e Objetivos do Projeto  
## Sistema de Atendimento Inteligente para Pesquisa de Peças

---

# 1. Visão Geral do Projeto

O projeto consiste na implementação de uma arquitetura modular para um sistema de atendimento inteligente voltado à pesquisa e determinação de peças automotivas.

A arquitetura foi projetada com separação clara de responsabilidades, permitindo:

- Escalabilidade
- Evolução incremental
- Integração com múltiplos canais
- Inserção progressiva de inteligência artificial
- Manutenção de regras de negócio determinísticas

A solução está estruturada em serviços independentes (containers Docker).

---

# 2. Estado Atual do Projeto (v0.1)

## 2.1 Arquitetura Implementada

Atualmente o sistema é composto por dois serviços principais:

### 1️⃣ docker-comm (Gateway / Orquestrador)

Responsável por:

- Receber mensagens via HTTP
- Manter sessão e histórico no Redis
- Normalizar o payload para o contrato técnico v1.0
- Encaminhar requisições ao docker-agent
- Retornar resposta estruturada ao chamador
- Aplicar regras operacionais (timeout, fallback, branch default)
- Registrar logs estruturados com trace_id

Características:

- Stateless (estado apenas no Redis)
- Multi-origem via `channel.name`
- Compatível com expansão para WhatsApp, Convert, Webchat, etc.

---

### 2️⃣ docker-agent (Agente Determinístico v0.1)

Responsável por:

- Receber request no contrato v1.0
- Validar regras obrigatórias
- Executar tool calling (atualmente mock)
- Aplicar regras determinísticas para:
  - Ambiguidade
  - Falta de resultado
  - Resultado único
- Retornar:
  - reply.text
  - actions
  - handoff
  - confidence
  - tool_trace

O agent atualmente opera de forma determinística (sem LLM).

---

## 2.2 Fluxo Atual

1. Mensagem entra no docker-comm.
2. Histórico é carregado do Redis.
3. docker-comm monta request padronizado.
4. docker-agent recebe e chama `search_parts` (mock).
5. Agent aplica regras de decisão.
6. Response retorna ao docker-comm.
7. docker-comm responde ao chamador.

---

## 2.3 Tool Atual (Mock)

A ferramenta `search_parts` simula busca:

- "bandeja" → retorna 2 itens (ambiguidade)
- "filtro de óleo" → retorna 1 item (caso único)
- Outros termos → 0 itens (handoff)

---

## 2.4 Estado Técnico Consolidado

✔ Arquitetura desacoplada  
✔ Contrato versionado (v1.0)  
✔ Separação por camadas (API / domínio / use case / infra)  
✔ Session management no gateway  
✔ Logs estruturados e rastreabilidade  
✔ Tool calling via porta  
✔ Containerização funcional  

---

# 3. Objetivos de Curto Prazo (Próxima Evolução)

## 3.1 Substituir Tool Mock por Motor de Busca Real

Implementar integração com um motor de busca real que:

- Consulte catálogo oficial (ERP ou base espelhada)
- Aplique regras de elegibilidade
- Retorne candidatos com score
- Permita filtros (ano, motor, aplicação, etc.)

Opções em avaliação:

- Reaproveitamento do motor atual como microserviço (recomendado)
- Consulta direta ao PostgreSQL
- Elastic/OpenSearch

---

## 3.2 Evoluir docker-agent para Orquestrador Inteligente

Adicionar camada de interpretação baseada em LLM com duas funções principais:

### 3.2.1 Pré-Busca
- Extrair entidades da mensagem
- Determinar se já há dados suficientes
- Identificar dados faltantes
- Formular perguntas de refinamento

### 3.2.2 Pós-Busca
- Analisar candidatos retornados
- Determinar se há item claro
- Identificar melhor critério de desambiguação
- Formular próxima pergunta
- Decidir handoff quando necessário

---

# 4. Fluxo Futuro Esperado (Arquitetura Alvo)

1. Usuário envia mensagem.
2. docker-comm normaliza e envia ao docker-agent.
3. LLM analisa mensagem (extração de entidades).
4. docker-agent chama motor de busca real.
5. Resultados retornam.
6. LLM avalia ambiguidade ou suficiência.
7. Sistema responde:
   - Item final,
   - Lista reduzida,
   - Ou pergunta de refinamento.

---

# 5. Objetivos Estratégicos do Projeto

- Construir sistema modular e escalável.
- Separar responsabilidades entre:
  - Gateway (transporte)
  - Agent (decisão)
  - Motor de busca (candidatos)
  - LLM (inteligência conversacional)
- Evitar acoplamento entre busca e decisão.
- Permitir evolução incremental sem reescrever arquitetura.
- Manter rastreabilidade e governança técnica.

---

# 6. Roadmap de Evolução

## Fase 1 (Atual)
Arquitetura base + agent determinístico + tool mock.

## Fase 2
Integração com motor de busca real.

## Fase 3
Integração de tool para preço/estoque.

## Fase 4
Inserção de LLM para interpretação e desambiguação inteligente.

## Fase 5
Aprimoramento de relevância, métricas e otimização de conversão.

---

# 7. Conclusão

O projeto encontra-se em estado estrutural sólido, com arquitetura preparada para evolução controlada.

A base atual permite:

- Testes ponta-a-ponta
- Validação de contrato
- Integração incremental de componentes reais
- Inserção futura de inteligência artificial sem reestruturação

O próximo passo crítico é substituir a busca mock por um motor de busca real, mantendo o docker-agent como orquestrador central do processo decisório.