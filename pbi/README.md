# O painel

A camada de apresentação, especificada em arquivos de texto em vez de um `.pbix`
versionado: binário em Git não rende revisão nem diff. O `.pbix` se monta a partir
deles em cerca de vinte minutos, pelo passo a passo de
[`MODELO.md`](MODELO.md#como-montar-o-pbix). O Power BI lê só
[`resultados/`](../resultados/LEIAME.md), nunca a SENATRAN.

| Arquivo | O que é |
|---|---|
| [`MODELO.md`](MODELO.md) | Modelo estrela: tabelas, grão, relacionamentos, decisões, ressalvas e tabela de validação |
| [`PAGINAS.md`](PAGINAS.md) | As cinco páginas do relatório, com a forma de cada visual e o porquê |
| [`REFRESH.md`](REFRESH.md) | Ciclo de atualização mensal e publicação no Service |
| [`powerquery/`](powerquery) | Onze consultas M: o parâmetro da pasta, uma por tabela do modelo e a função que monta a chave de município |
| [`dax/`](dax) | `dCalendario` e as medidas |
| [`tema.json`](tema.json) | Tema do Power BI, com paleta categórica verificada para daltonismo |

Duas coisas que o painel precisa deixar claro:

- **frota é estoque registrado, não emplacamento**: somar meses não dá o ano, e a
  variação mensal é saldo, não venda;
- **a divisão entre plug-in e híbrido convencional não vale pelo campo
  combustível**, que registra com rótulo próprio só 22% dos plug-ins vendidos. O
  painel ainda tira a tecnologia dessa base; a troca é a pendência 5 do item 8 de
  [`docs/ROTEIRO.md`](../docs/ROTEIRO.md).
