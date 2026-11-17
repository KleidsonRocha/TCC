# Reconciliação da publicação de evidências

Publicação preparada em 17/11/2026 para atender à pré-revisão. O commit
`52e4d74` continua identificando o código da ablação final; o novo commit
documental disponibiliza os registros que estavam fora do Git.

- Tabelas 5 e 6: resultados históricos distintos, com seus registros, avaliadores
  e anotações. Não estimam ganho causal da versão final.
- Tabela 7: comparação qualitativa relatada no artigo. As saídas completas do
  Elasticsearch de 05/10 não foram localizadas; não se atribui reprodutibilidade
  quantitativa a essa comparação.
- Tabelas 8 e 9: modelo base e adapter LoRA BF16 no experimento de 19/10. A
  triagem cadastral não é acurácia comercial. QLoRA e promoção do adapter no
  Ollama não são entregas desse experimento.
- Tabela 10: três repetições, duas condições e 568 IDs por repetição/condição,
  totalizando 3.408 registros. A LLM participou de 45/371 conversas em H; esse
  número não se confunde com os 71/371 da comparação de fine-tuning anterior.
- Tabela 11: três rubricas auxiliares retrospectivas. Os metadados originais
  foram preservados. A conferência por dois profissionais, com 10 e 7 anos de
  experiência, foi declarada pelo autor; não há vínculo de notas individuais,
  cegamento ou independência documentados que permita rebatizar essas séries
  como avaliações individuais dos profissionais.

A fonte cadastral também precisa ser distinguida do código: os objetos LFS de
contingência do commit são de 14/09 (1.776.907 aplicações), enquanto o laboratório
usou a exportação de 19/10 (1.779.443 aplicações). Ambos possuem 52.798 produtos,
com hashes diferentes. O catálogo experimental exato está publicado em
`catalogo_20261019/`; o código e o snapshot operacional não foram alterados.

O arquivo [RESPOSTAS_PARA_O_TCC.md](documentacao_recebida/RESPOSTAS_PARA_O_TCC.md)
e [AUDITORIA_DA_REVISAO.json](documentacao_recebida/AUDITORIA_DA_REVISAO.json)
foram copiados sem mudar seus números ou datas. O registro de conferência
profissional complementa, sem apagar, os metadados do pacote recebido.

O [conferidor](reproducao/conferir_resultados.py) e o manifesto da publicação são
novos. Os avaliadores originais e as evidências selecionadas conservam seus
bytes e hashes. O pacote técnico é um recorte identificado da entrega original:
o dump de catálogo e cópias redundantes dos objetos LFS foram omitidos, conforme
[VERSAO_EXPERIMENTAL.json](VERSAO_EXPERIMENTAL.json).
