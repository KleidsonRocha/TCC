# Relatório comparativo do Qwen original e do modelo adaptado

Experimento de 19 de outubro de 2026

Experimento realizado em 19 de outubro de 2026. Relatório técnico para documentação do TCC e consulta das evidências. A comparação mostra que o adapter treinado não melhorou o desempenho geral na configuração avaliada. O candidato foi mais lento, teve menor aprovação no golden isolado e produziu mais saídas JSON incompletas. O modelo original permaneceu como referência e o candidato não foi promovido.

## 1 Objetivo e identidade dos modelos

O objetivo foi medir o efeito de um adapter supervisionado na tarefa de pré-busca de autopeças: decidir search, ask ou handoff, preencher critérios estruturados, conduzir perguntas e evitar códigos sem evidência. O treino não adicionou o catálogo inteiro aos pesos nem substituiu o mecanismo de pesquisa no ERP. A aplicação continuou responsável pelos filtros, estado da conversa, regras obrigatórias e apresentação dos itens.

| Condição | Original | Ajustado |
| --- | --- | --- |
| Identificador da avaliação | qwen-base-bf16 | qwen-ft-bf16 |
| Backbone | Qwen/Qwen2.5-7B-Instruct | O mesmo backbone |
| Revisão fixa | a09a35458c702b33eeacc393d103063234e8bc28 | a09a35458c702b33eeacc393d103063234e8bc28 |
| Adapter | Desabilitado | Adapter LoRA final habilitado |
| Motor e precisão | Transformers e BF16 | Transformers e BF16 |
| Quantização na comparação | Nenhuma | Nenhuma |

O original comparado foi a versão Hugging Face em BF16. Não foi uma repetição do artefato quantizado qwen2.5:7b do Ollama. Portanto, os resultados medem o efeito do adapter nesse ambiente controlado; não demonstram desempenho, latência ou compatibilidade de um futuro pacote Ollama.

## 2 Dados e execução do treinamento

O dataset pre-search-ft-v1 contém exemplos de mensagens e respostas estruturadas. Há 163 registros distribuídos em 128 de treino, 19 de validação e 16 de teste retido. Esses 16 registros não são os 27 casos golden e não são as 371 conversas por categoria. O trainer carrega treino e validação; a comparação formal descrita neste relatório usa as duas baterias externas congeladas. Não há, neste consolidado, uma métrica separada de avaliação dos 16 registros retidos.

| Parâmetro efetivo | Valor |
| --- | --- |
| Método | LoRA com modelo carregado em BF16; load_in_4bit=false |
| GPU | NVIDIA RTX PRO 6000 Blackwell Server Edition; instância anunciada com 96 GB de VRAM |
| Épocas e passos | 2 épocas; 32 passos globais |
| Batch por dispositivo e acumulação | 1 exemplo; acumulação de 8 passos |
| Taxa de aprendizado e warm-up | 0,0001 e proporção 0,03 |
| Comprimento máximo | 2048 tokens; packing=false |
| Configuração LoRA | r=16; alpha=32; dropout=0,05; bias=none |
| Módulos treináveis | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Memória e precisão | Gradient checkpointing; bf16=true; fp16=false |
| Seed | 42 |
| Duração registrada do treino | 172,6038 segundos, aproximadamente 2 min 53 s |
| Loss média de treino | 1,4185253810 |
| Loss de validação final reportada | 0,3719895780 |
| Seleção de checkpoint | Script com load_best_model_at_end; estado registra melhor passo 30; checkpoints 30 e 32 preservados |

O experimento executado foi LoRA, não QLoRA em 4 bits: o resumo registra load_in_4bit=false e torch.bfloat16. O script também oferece uma opção QLoRA, mas sua existência não comprova que ela foi usada nesta execução. Os parâmetros acima foram conferidos no resumo, adapter_config.json e campos escalares de training_args.bin, lidos sem desserializar objetos executáveis.

A configuração salva tem assistant_only_loss=false e completion_only_loss=None; não se deve descrever este treino como explicitamente mascarado para aprender somente os tokens do assistente. Há limite de sequência em 2048 tokens, mas a taxa de truncamento do dataset de treino não foi medida neste relatório. A loss de validação não é taxa de acerto comercial e não demonstra melhoria no atendimento.

Os pesos base e o adapter permanecem separados. O adapter depende do backbone original para inferência. Não houve merge, quantização do candidato, importação validada no Ollama ou promoção automática.

## 3 Como a comparação foi conduzida

| Aspecto | Procedimento registrado |
| --- | --- |
| Conjuntos | 371 conversas por categoria e subcategoria e 27 casos golden para cada modelo |
| Volume | 398 registros por modelo; 796 registros ponta a ponta; 1169 turnos somados |
| Golden adicional | 54 verificações de validador isolado, duas versões de cada um dos 27 casos; não são mais 54 conversas independentes |
| Backend | Mesmo código congelado, catálogo, regras, montagem do fluxo e parâmetros |
| Fonte ERP | Snapshot contrato v2: 52798 produtos e 1779443 aplicações |
| Consistência da fonte | Exportação repeatable-read e somente leitura; PostgreSQL isolado para avaliação |
| Inferência | BF16, greedy, temperatura 0, limite de 220 tokens, lm-format-enforcer com JSON Schema |
| Execução | Um caso por vez; até 8 turnos por conversa de categoria; uma rodada por condição |
| Transporte | Inferência em GPU remota por túnel SSH temporário; backend de avaliação isolado |
| Ordem dos jobs | Ajustado categorias; original categorias; ajustado golden; original golden |
| Captura operacional | Gravação na fila de treino desabilitada; gateway, Redis e WhatsApp fora da comparação |

A bateria parte das mesmas mensagens iniciais e referências para os dois modelos. Os follow-ups são governados pelo avaliador e pelo que o sistema pergunta, com base nos fatos de referência; por isso duas conversas podem ter quantidades diferentes de turnos. Trata-se de comparação pareada por caso, não de transcrições artificialmente idênticas em todos os turnos. As 371 entradas cobrem 24 categorias e 347 subcategorias; essa distribuição não comprova cobertura de todos os produtos, veículos ou aplicações.

Há duas observações no golden: a saída do validador isolado e, separadamente, o atendimento completo com bypass determinístico e pesquisa. Mesmo no conjunto isolado, as contagens registram 25 chamadas LLM por modelo, pois parte do validador resolve entradas antes da inferência. No fluxo completo do golden houve duas chamadas LLM por modelo. Não se devem somar essas observações como casos independentes.

A tentativa inicial de instrumentação foi interrompida por incompatibilidade do lm-format-enforcer 0.11.3 com parte do JSON Schema. Aplicou-se a correção documentada em patch_decoder.py e as rodadas oficiais foram reiniciadas. instrumentation_attempt_v1 e as sondagens com limite de 512 tokens foram excluídas das métricas oficiais. Ambos os modelos permaneceram com 220 tokens na comparação final.

## 4 Resultados de qualidade

| Métrica | Original | Ajustado |
| --- | --- | --- |
| Golden isolado aprovado | 27/27 = 100% | 24/27 = 88,9% |
| Golden sem coincidência exata com treino | 21/21 = 100% | 18/21 = 85,7% |
| Critérios esperados corretos no golden | 100% | 98,88% |
| Conversas com itens coerentes com cadastro | 133/371 = 35,8% | 131/371 = 35,3% |
| Suspeitas de item incorreto | 4 | 3 |
| Conversas com filtros veiculares divergentes | 16 | 13 |
| Erros técnicos nos turnos por categoria | 0 | 0 |

| Triagem das 371 conversas | Original | Ajustado |
| --- | --- | --- |
| Handoff por dado desconhecido | 105 | 106 |
| Itens coerentes com cadastro | 133 | 131 |
| Fluxo não concluiu com itens na fonte | 61 | 63 |
| Sem itens na subcategoria de referência | 34 | 34 |
| Suspeita de falso negativo | 34 | 34 |
| Suspeita de item incorreto | 4 | 3 |

A classificação final permaneceu igual em 365 das 371 conversas, ou 98,4%. Houve mudança em seis classificações e em mensagens do assistente de 19 conversas. Os pequenos ganhos de triagem — uma suspeita a menos de item incorreto e três divergências veiculares a menos — não vieram acompanhados de maior recuperação de itens coerentes. Dois casos antes classificados como coerentes passaram a suspeita de falso negativo.

As três regressões do candidato no golden isolado foram search_oil_viscosity_5w40, search_oil_viscosity_hyphen e search_multi_item_gate_radiador_bandeja. São duas formas de solicitar óleo 5W40 e um pedido múltiplo de radiador e bandeja. Nesses três casos específicos, o atendimento completo foi resolvido deterministicamente e teve respostas e buscas idênticas entre original e ajustado. A falha isolada não deve ser descrita como falha do atendimento completo.

## 5 Latência e integridade do JSON

| Métrica por categorias | Original | Ajustado |
| --- | --- | --- |
| Turnos | 557 | 558 |
| Média por turno em segundos | 2,900 | 3,435 |
| Mediana por turno em segundos | 0,955 | 0,921 |
| P95 por turno em segundos | 15,003 | 19,402 |
| Média do turno que chama LLM em segundos | 13,489 | 17,346 |
| Média da busca em segundos | 0,080 | 0,081 |
| Conversas que chamaram LLM | 71/371 = 19,1% | 71/371 = 19,1% |
| Chamadas LLM | 80 | 80 |
| Tokens gerados | 10898 | 15229 |
| JSON bruto completo | 57/80 = 71,3% | 36/80 = 45,0% |
| Saídas cortadas no limite | 23/80 = 28,8% | 44/80 = 55,0% |
| Turnos com fallback da LLM no backend | 18 | 36 |

A média por turno aumentou 18,4%; o P95 aumentou 29,3%. Nos turnos que chamaram a LLM, o aumento da média foi de 28,6%. O candidato gerou 39,7% mais tokens. Essas diferenças são descritivas desta rodada, sem inferência estatística de superioridade ou causalidade isolada.

A mediana baixa é dominada pelos caminhos determinísticos. Somente 71 conversas por versão chamaram a LLM; as demais não testam diretamente a capacidade do adapter. O maior volume de tokens e os cortes frequentes são compatíveis com parte da regressão de latência e de JSON, mas este experimento não separou experimentalmente o custo do adapter, a verbosidade e o custo do decodificador.

Os tempos ponta a ponta incluem backend local e transporte SSH, excluem a inspeção independente da fonte e não incluem WhatsApp ou gateway. Não são tempos de atendimento do canal de produção. A quantidade diferente de turnos também altera a composição da média. O JSON bruto incompleto não é erro HTTP: o fallback do backend pode preservar o atendimento apesar da falha de geração, o que explica zero erros técnicos com pior integridade da saída bruta.

## 6 Limitações e proteção da interpretação

Seis mensagens iniciais do golden coincidem exatamente com exemplos de treino. Os 21 casos sem coincidência são apresentados separadamente, mas continuam sem garantia de independência de paráfrases ou de modelos de conversa compartilhados. Nos 371 casos não foram encontradas coincidências exatas das mensagens iniciais; isso também não exclui similaridade semântica.

O avaliador golden existente confere campos esperados e não reprova genericamente todos os campos extras. Aprovação de 100% não significa validação semântica integral. Os julgamentos por categoria são triagem de coerência com cadastro, dependem da referência e exigem revisão humana; não certificam encaixe físico, preço, estoque ou inexistência de produtos fora da classificação consultada.

A auditoria posterior encontrou referências inadequadas, pedidos contraditórios e falhas determinísticas de formação de filtros. Assim, as 34 suspeitas de falso negativo de cada condição não são uma taxa confirmada de falha da LLM ou do motor de busca. As 34 subcategorias vazias não demonstram ausência da peça em todo o catálogo. A auditoria histórica com 1776907 aplicações corresponde a outro recorte; a fonte oficial desta comparação tem 1779443 aplicações, conforme seu manifesto, e as contagens não devem ser misturadas.

Houve uma rodada por modelo, em ordem fixa, sem repetições, randomização da ordem, intervalos de confiança ou benchmark de carga. Não se pode atribuir toda a diferença de latência exclusivamente ao adapter. A redução da loss durante o treino não eliminou regressões de geração. Nenhuma nova avaliação dos 371 casos foi feita para compor este relatório: ele consolida e confere os registros congelados.

## 7 Decisão e relação com as correções posteriores

Na configuração avaliada, o fine-tuning não justificou promoção: perdeu aprovação no golden isolado, não aumentou os casos coerentes e piorou a latência e a completude do JSON. A decisão foi manter o original como referência e adiar nova adaptação. O resultado é válido para esta configuração e não demonstra que todo fine-tuning futuro será ineficaz.

Antes de outra rodada, convém corrigir referências de teste e critérios de aprovação, proteger splits por conversa, alinhar o contrato de prompt e payload entre treino e execução, revisar a supervisão dos tokens, medir truncamento e controlar concisão/limite de geração igualmente nas duas condições. Essas são propostas metodológicas; não foram executadas como novo treinamento neste relatório.

As correções posteriores de aliases, identidade da peça, aplicação veicular, follow-ups, ABS e sugestões de motor por ano pertencem ao backend e ao catálogo. Os retestes Omni/Convert com Clio, S10, Gol e FH 460 foram realizados depois do experimento congelado. Seus resultados não são ganhos do adapter e não alteram retroativamente a tabela comparativa. Uma medição da versão atual exige nova rodada identificada separadamente.

## 8 Onde estão os testes e como consultar

O ZIP deste relatório é uma cópia de consulta e auditoria dos testes; não inclui pesos, checkpoints binários ou o dump completo do banco. Todas as 796 conversas individuais e as exportações de mensagens, chamadas, buscas e tempos estão incluídas em evidencias/comparacao. Os caminhos abaixo são relativos à pasta extraída do relatório.

| Arquivo ou pasta | Uso |
| --- | --- |
| [LEIA-ME.md](LEIA-ME.md) | Instruções de leitura e composição do pacote |
| [comparação pesquisável](evidencias/comparacao/comparison.html) | Abrir no navegador; localizar caso, mensagens e diferenças entre os modelos |
| [paired_conversations.json](evidencias/comparacao/paired_conversations.json) | Todas as conversas pareadas completas |
| [case_comparison.csv](evidencias/comparacao/case_comparison.csv) | Comparação por caso para abrir em planilha |
| [métricas derivadas](metricas_comparativas.csv) | Tabela numérica original versus ajustado com unidade e escopo |
| [golden por caso](golden_por_caso.csv) | 27 pares com aprovação e marcação de coincidência no treino |
| [entradas das 371 conversas](evidencias/comparacao/cases_371.json) | Mensagens iniciais, classificação e referências congeladas |
| [golden_27.json](evidencias/comparacao/golden_27.json) | Entradas e expectativas do golden |
| evidencias/comparacao/qwen-base-bf16/categories/conversations/ | 371 registros individuais do original |
| evidencias/comparacao/qwen-ft-bf16/categories/conversations/ | 371 registros individuais do ajustado |
| evidencias/comparacao/qwen-base-bf16/golden/conversations/ | 27 casos com saída isolada e execução completa do original |
| evidencias/comparacao/qwen-ft-bf16/golden/conversations/ | 27 casos com saída isolada e execução completa do ajustado |
| [turns.jsonl](evidencias/comparacao/turns.jsonl) | Um registro por turno, com mensagens, tempos e estado |
| [searches.jsonl](evidencias/comparacao/searches.jsonl) | Consultas, filtros, itens retornados e diagnósticos capturados |
| [llm_calls.jsonl](evidencias/comparacao/llm_calls.jsonl) | Payloads, respostas brutas, tokens e tempos da LLM |
| [summary original](evidencias/comparacao/comparison_summary.json) | Métricas consolidadas usadas como fonte |
| [coincidências do dataset](evidencias/comparacao/dataset_overlap.json) | Identificadores dos seis golden coincidentes |
| evidencias/treinamento/dataset/ | Mensagens, registros, splits, prompt e manifesto do treino |
| [parâmetros extraídos](parametros_treino_verificados.json) | Campos escalares lidos de training_args.bin sem unpickling |
| evidencias/comparacao/frozen_code/ | Código congelado de aplicação e avaliadores |
| [verificação deste relatório](verificacao_relatorio.json) | Recontagem de registros, médias, aprovações e hashes |
| [inventário de arquivos](inventario_arquivos.csv) | Caminho, tamanho e SHA-256 dos arquivos entregues |

Para uma auditoria manual, escolha o ID em case_comparison.csv, abra o mesmo ID nos diretórios dos dois modelos e compare initial_message, turns, response, conversation_state, searches, stop_reason e verdict. No golden, compare validator_response e evaluation primeiro; depois examine end_to_end. Não confunda o código da referência com um produto efetivamente retornado. O HTML pesquisável facilita a leitura, mas os JSONs individuais são a evidência detalhada.

## 9 Modelos preservados e reprodução

O arquivo completo local permanece em D:/TCC/docker-agent/fine_tuning_gpu/experimento_qwen_2026-10-19. O modelo original está em modelo/base; o adapter em modelo/ajustado/adapter; os checkpoints em treinamento/execucao_original; o snapshot e catalog.dump em comparacao. Esses arquivos maiores não foram duplicados no ZIP do relatório. O inventário original e verificacao_pacote.json registram a verificação feita em 19/10, com 1213 arquivos e aproximadamente 17,48 GB; esse é um registro histórico de integridade, não uma nova conferência de todos os pesos neste relatório.

Nesta preparação foram reconferidos o hash do adapter, os hashes das duas baterias, as contagens de registros, as classificações, as médias de latência de categoria e as aprovações golden. A revisão do backbone é a09a35458c702b33eeacc393d103063234e8bc28. O SHA-256 do adapter usado na comparação é 3046e3e9145bf3b7eb0dc4f37c673f8bfb2c214368526582dbe143eb995f1a54.

Para reproduzir, copie os artefatos para uma nova área de trabalho, prepare um ambiente compatível com as versões salvas em server_manifest.json e gpu_dependencies.txt, restaure catalog.dump apenas em PostgreSQL isolado, use o snapshot e código congelados e configure o servidor com base mais adapter. Use os mesmos parâmetros de geração e repita as duas baterias com saídas em diretório novo. Alguns scripts preservam caminhos da execução original: adapte esses caminhos e nunca execute run_all.py diretamente sobre a pasta arquivada, pois ele grava resultados. O pacote não é um instalador de ambiente e não depende de acesso à VPS antiga.

O carregador local reproducao/carregar_modelo.py permite inferência offline após instalar as dependências e provisionar memória compatível, mas não substitui o protocolo formal nem aplica necessariamente suas restrições JSON. A importação do adapter no Ollama e o carregamento completo local não foram validados no experimento arquivado. Para detalhes e comandos preservados, consulte o LEIA-ME do experimento original.

## 10 Fontes primárias e conclusão para o TCC

As fontes primárias são os manifestos de execução, training_summary.json, adapter_config.json, training_args.bin, trainer_state.json, os quatro diretórios de casos individuais e comparison_summary.json. Não foram utilizadas referências externas para preencher resultados ou parâmetros ausentes. Cópias dos documentos de apoio e dos arquivos de fonte selecionados acompanham o pacote; as evidências originais permanecem intactas.

Conclusão sugerida para o TCC: o treinamento supervisionado de um adapter LoRA para Qwen2.5-7B-Instruct foi executado e avaliado em protocolo pareado, com 371 conversas por categoria e 27 casos golden por condição. Na configuração BF16 e limite de 220 tokens, o candidato não superou o original: houve regressão no golden isolado, maior latência e menor completude do JSON, sem aumento da recuperação coerente. A forte participação do backend determinístico e as limitações das referências exigem separar qualidade da LLM, qualidade da busca e comportamento do atendimento completo. O candidato foi preservado para estudo e não foi promovido.
