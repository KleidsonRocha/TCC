# Evidências e reprodução das Tabelas 5 a 11

Este diretório publica os registros de pesquisa antes guardados em pastas locais
ignoradas pelo Git. O código da ablação final é o commit
`52e4d7460009d9635445c8ca69c604488b5dacef`; a publicação das evidências é posterior.
Nenhuma inferência, classificação ou medição foi refeita para substituir os
resultados históricos nesta publicação. A correspondência tabela/script/origem
está na seção [Reprodução dos resultados](../README.md#reprodução-dos-resultados).

## Abrir os resultados

- [01_tecnico.zip](01_tecnico.zip): extraia em uma pasta nova. Abra
  `relatorio_avaliacao_final.html` e `leitor_conversas.html`. O diretório
  `tecnico/runs/` contém os 3.408 registros oficiais, com mensagens, critérios,
  produtos e tempos; `tecnico/inputs/` preserva as entradas e a referência dos
  splits. Código, runner, agregador, protocolo, congelamento, dependências,
  auditorias e controles também estão incluídos.
- [02_rubricas.zip](02_rubricas.zip): cópia integral e inalterada do pacote de
  revisão recebido em 27/10. Extraia para consultar `RELATORIO_371.md`,
  `avaliacoes_371.csv`, `avaliacao_IA_*_V3.json`, chave A/B e `reproducao/`.
  Para leitura direta no Forge, o [relatório](rubricas/RELATORIO_371.md), as
  [métricas](rubricas/metricas_por_configuracao.json) e os
  [scripts/critérios](reproducao/rubricas/avaliar_371.py) também estão separados.
- [Catálogo experimental de 19/10](catalogo_20261019/manifest.json): os dois
  CSVs gzip exatos usados na avaliação final, com 52.798 produtos e 1.779.443
  aplicações. Não é o snapshot de contingência de 14/09 do código versionado.
- [03_fine_tuning](03_fine_tuning/comparison.md): relatórios da comparação
  BF16/LoRA de 19/10 e [ZIP dos registros de entrada do agregador](03_fine_tuning/registros_20261019.zip).
  Esse experimento não é a ablação final e não promoveu o adapter no Ollama.
- [04_ranking](04_ranking/comparacao_ranking.md): saídas de 29/09 e da execução
  pareada, anotações e avaliador da coorte histórica. Os JSONs mantêm as chaves de
  cenário/turno/item necessárias ao pareamento.
- [05_desempenho](05_desempenho/deterministic_ask_comparison_2026-08-27.md):
  antes/depois de `deterministic_ask`, com os dois conjuntos de 50 registros e o
  comparador original. Trata-se de outro experimento, anterior à ablação final.
- [06_elasticsearch](06_elasticsearch/LEIA_ME.md): estado da evidência qualitativa
  da Tabela 7. As saídas originais completas não foram localizadas.
- [Documentação recebida](documentacao_recebida/RESPOSTAS_PARA_O_TCC.md): adendo,
  auditoria e declaração do autor sobre a conferência profissional. Leia também a
  [reconciliação de proveniência](ADENDO_RECONCILIACAO.md).

## Conferir sem GPU e sem acesso ao ERP

Na raiz do repositório, com Python >= 3.11:

```text
python -X utf8 evidencias/reproducao/conferir_resultados.py
python -X utf8 evidencias/reproducao/conferir_resultados.py --recalcular --saida .tmp/conferencia_artigo
```

O primeiro comando valida hashes, tamanho dos arquivos, CRC dos ZIPs, quantidade
de casos oficiais e hashes do código congelado. O segundo executa os agregadores
originais sobre cópias novas, compara as métricas às arquivadas e grava
`VERIFICACAO.json`. Nenhuma chamada de rede ou inferência é feita. Use outra pasta
de saída se já houver uma conferência anterior.

A [conferência desta publicação](CONFERENCIA_PUBLICACAO.json) registra a
recomputação local de 17/11/2026: Tabelas 5, 6 e 8–11 correspondentes às fontes,
incluindo a reexecução das regras das rubricas. Isso não certifica a publicação
no Forge nem recupera as saídas ausentes do Elasticsearch.

Para reexecutar também as regras semânticas originais da Tabela 11:

```text
python -X utf8 evidencias/reproducao/conferir_resultados.py --recalcular --rubricas --saida .tmp/conferencia_com_rubricas
```

Essa opção prepara o cache cadastral a partir dos CSVs de `catalogo_20261019/`, confere os
hashes, executa `preparar_evidencias.py` e `avaliar_371.py` originais e compara
todas as contagens às originais. Recontar rótulos e reexecutar regras de rubrica
são verificações distintas; ambas são informadas separadamente no resultado.
As rubricas são auxiliares e retrospectivas. Não representam três avaliadores
humanos independentes nem uma adjudicação profissional por caso.

## Congelamento, arquivos grandes e limites

[VERSAO_EXPERIMENTAL.json](VERSAO_EXPERIMENTAL.json) registra a comparação dos
178 arquivos congelados que possuem correspondente no commit citado. A única
divergência é `docker-agent/docs/TODO.md`. Para texto, a comparação normaliza
apenas CRLF/LF; objetos LFS são comparados pelo SHA-256 do conteúdo. Os bytes
originais do código congelado permanecem no ZIP.

Para evitar duplicação, o ZIP técnico não inclui as cópias grandes de
`candidates.csv.gz` e `applications.csv.gz`. A fonte experimental exata está em
[catalogo_20261019](catalogo_20261019/manifest.json), como arquivos Git comuns,
com hashes conferidos. O snapshot de contingência do commit, em
[docker-agent/db/init/fallback/v2](../docker-agent/db/init/fallback/v2/manifest.json),
é de 14/09 e contém 1.776.907 aplicações; a fonte experimental de 19/10 contém
1.779.443 aplicações. Os 52.798 produtos têm a mesma contagem, mas os arquivos
também têm hashes diferentes. Não se pode substituir uma fonte pela outra.
O snapshot antigo acompanha o código congelado por referência LFS, sem alterar
o runtime atual para publicar o novo conjunto. O pacote tampouco publica o dump
local do catálogo de 74 MB: ele não
é necessário para conferir os resultados arquivados. Os arquivos omitidos e
seus hashes estão no registro de versão; o pacote não se declara uma cópia
integral da entrega original. Os manifestos originais foram preservados e não
foram regenerados para ocultar essas omissões.

`tecnico/REPRODUCAO.md` é o roteiro histórico do laboratório e se refere à
entrega integral original, inclusive ao dump. Para uma nova execução de
inferência, é preciso reconstruir e verificar o mesmo estado cadastral,
dependências, modelo/digest e condições de CPU. A conferência disponibilizada
aqui reproduz os cálculos dos resultados existentes; não promete uma réplica de
inferência idêntica nem execução contínua, cega ou comercialmente independente.

O relatório histórico foi escrito antes da revisão recebida. Suas menções a
revisão humana pendente registram aquele momento; a declaração posterior está
em [REGISTRO_DA_REVISAO_PROFISSIONAL.json](documentacao_recebida/REGISTRO_DA_REVISAO_PROFISSIONAL.json).
Não foram fabricadas fichas ou notas individuais para preencher essa lacuna.

## Integridade, dados e publicação no Forge

[MANIFESTO.json](MANIFESTO.json) contém os hashes da publicação. A
[proveniência](PROVENIENCIA.json) relaciona cada arquivo selecionado, inclusive
os membros dos ZIPs, à fonte local original e ao hash. A revisão de dados
selecionou saídas de laboratório, identificadores de casos e dados de catálogo;
não publica `.env`, chaves de acesso, pesos dos modelos ou backups de atendimento.
Os nomes/códigos de peças e aplicações são mantidos porque sustentam a avaliação.

A seleção foi inspecionada para campos preenchidos de credenciais/contato e
padrões de tokens, chaves privadas e e-mails. Esse controle é limitado ao material
selecionado, não constitui auditoria integral de todo o histórico do Git.

O espelhamento para o Forge depende do push e da Action. Confirme o commit novo,
a presença deste diretório e a execução do conferidor em um clone do Forge.
Para executar o runtime do commit, confirme também que `git lfs pull` baixa os
CSVs de contingência reais, e não somente os ponteiros de texto. A conferência
das rubricas usa os arquivos Git comuns do catálogo experimental. O sucesso local desta
preparação não comprova publicação remota.
