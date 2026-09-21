# Lista de validacao humana da bateria real

Estes cenarios ja possuem validacoes automatizadas estruturais. A revisao abaixo serve para promover expectativas comerciais; ela nao deve ser preenchida pelo modelo.

Marque cada item depois de testar no Streamlit e registre a resposta esperada quando houver produto, discriminador ou handoff especifico.

- [ ] **search_001 — complete_search**
  - conversa: `radiador gol 2010 1.0`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_003 — complete_search**
  - conversa: `radiador ecosport 2008 1.6`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_006 — complete_search**
  - conversa: `coxim amortecedor ecosport 2008 1.6`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_011 — complete_search**
  - conversa: `pastilha de freio gol 2010 1.0 dianteira`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_016 — complete_search**
  - conversa: `disco de freio gol 2010 1.0 dianteiro`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_021 — complete_search**
  - conversa: `bandeja ecosport 2008 esquerda`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **search_026 — complete_search**
  - conversa: `filtro de oleo gol 2010`
  - por que revisar: O ERP pode mudar candidatos, discriminador e ordenacao.
  - validar: A familia entendida, os filtros e o primeiro discriminador fazem sentido comercialmente?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_001 — result_disambiguation**
  - conversa: `radiador gol 2010 1.0` → `1`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_002 — result_disambiguation**
  - conversa: `radiador ecosport 2008 1.6` → `nenhuma dessas`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_003 — result_disambiguation**
  - conversa: `coxim amortecedor ecosport 2008 1.6` → `quero falar com um vendedor`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_004 — result_disambiguation**
  - conversa: `bandeja ecosport 2008 esquerda` → `2`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_005 — result_disambiguation**
  - conversa: `radiador focus 2010 1.6` → `talvez` → `aquela` → `indefinido`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_006 — result_disambiguation**
  - conversa: `radiador gol 2010 1.6` → `1`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_007 — result_disambiguation**
  - conversa: `coxim amortecedor gol 2010 1.0` → `nenhuma dessas`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_008 — result_disambiguation**
  - conversa: `bandeja ecosport 2008 direita` → `2`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_009 — result_disambiguation**
  - conversa: `radiador ecosport 2008 zetec rocam` → `a primeira`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_010 — result_disambiguation**
  - conversa: `radiador motor gol 2010 1.0` → `nao sei` → `aquela` → `indefinido`
  - por que revisar: A selecao depende dos atributos e candidatos atuais do ERP.
  - validar: As opcoes apresentadas distinguem produtos de forma compreensivel e a resposta final escolhe o item correto?
  - resultado esperado aprovado: _preencher_

- [ ] **disambiguation_correction_001 — result_disambiguation_correction**
  - conversa: `radiador Gol 2010 1.0` → `corrigindo, o carro e um Corsa 2011 1.4`
  - por que revisar: A correcao precisa descartar os candidatos da aplicacao anterior antes de pesquisar de novo.
  - validar: A segunda busca usa somente Corsa 2011 1.4 e nao permite selecionar um candidato do Gol?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_001 — semantic_or_policy**
  - conversa: `meu carro esta esquentando, o que pode ser?`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_002 — semantic_or_policy**
  - conversa: `tem aquilo que segura o carro?`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_003 — semantic_or_policy**
  - conversa: `a peca faz barulho quando viro`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_004 — semantic_or_policy**
  - conversa: `quero falar com um vendedor`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_005 — semantic_or_policy**
  - conversa: `preciso de uma peca mas nao sei o nome`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_006 — semantic_or_policy**
  - conversa: `voces vendem pneu?`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_007 — semantic_or_policy**
  - conversa: `quero trocar o oleo inteiro`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_008 — semantic_or_policy**
  - conversa: `o carro nao liga`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_009 — semantic_or_policy**
  - conversa: `tem uma coisa perto do motor vazando`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_

- [ ] **policy_010 — semantic_or_policy**
  - conversa: `agora quero uma bateria para o carro`
  - por que revisar: Descricao funcional, sintoma ou politica de handoff nao possui uma unica resposta objetiva.
  - validar: A resposta e segura, nao confirma familia por fuzzy inseguro e pergunta ou transfere no momento correto?
  - resultado esperado aprovado: _preencher_
