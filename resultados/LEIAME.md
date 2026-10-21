# Resultados

Gerado por `eletromobilidade publicar` a partir de `data/processed` em 2026-10-21 18:40 UTC (código no commit `807e3be`). Não edite à mão: rode `processar` e `publicar` de novo.

## Cobertura

- **Base por combustível:** jun/2020 a set/2026, 75 meses; faltam jan/2022.
- **Base por modelo:** 2 meses (dez/2020, set/2026).
- **Conciliação:** 2 meses (dez/2020, set/2026).
- **Municípios:** 5.571 com código IBGE, 7 deles publicados pela SENATRAN com mais de uma grafia na série; sem código: NAO IDENTIFICADO, NAO SE APLICA, SEM INFORMACAO.
- Ajuste em d_frota_por_uf_municipio_combustivel_novembro_2021.xlsx (nov/2021): contagens divididas por 10 (todas eram múltiplas de 10 no arquivo publicado).
- Ajuste em d_frota_por_uf_municipio_combustivel_janeiro_2022.xlsx (jan/2022): idêntico a 2021-12; excluído da série.
- Ajuste em d_frota_por_uf_municipio_combustivel_abril_2022.xlsx (abr/2022): frota_hibrido_plug_in: classe sem registro até 2022-04; antes disso os veículos dela estão em outra classe.
- Ajuste em d_frota_por_uf_municipio_combustivel_novembro_2022.xlsx (nov/2022): frota_celula_combustivel: classe sem registro até 2022-11; antes disso os veículos dela estão em outra classe.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---:|---|
| `combustivel_brasil.csv` | 75 | Base por combustível: frota por classe, total, eletrificada e participação, Brasil, por mês. |
| `combustivel_uf.csv` | 2.025 | Idem, por UF. |
| `combustivel_municipio.parquet` | 417.997 | Idem, por município. |
| `combustivel_eletrificados.parquet` | 725.874 | Base por combustível: rótulos eletrificados por município e mês. |
| `combustiveis_classificados.csv` | 30 | Auditoria: rótulos de combustível, classe atribuída e total de veículos. |
| `modelo_brasil.csv` | 2 | Base por modelo: frota por classe (inclui plug-in x convencional e híbrido leve), Brasil, por mês. |
| `modelo_uf.csv` | 54 | Idem, por UF. |
| `modelo_municipio.parquet` | 11.147 | Idem, por município. |
| `modelo_eletrificados.parquet` | 195.356 | Base por modelo: eletrificados e híbridos leves por município, modelo e ano de fabricação. |
| `modelos_classificados.parquet` | 70.869 | Auditoria: cada modelo, classe, regra aplicada, total, marca, marcação 'revisar' e confronto com a tabela PBE Veicular do Inmetro. |
| `modelos_dimensao.parquet` | 935 | Dimensão de marca e modelo: grafia do RENAVAM, marca canônica e origem, por modelo distinto. |
| `municipios_dimensao.parquet` | 5.574 | Dimensão de município: código IBGE, nome oficial, UF e as grafias com que a SENATRAN publicou o município na série. |
| `conciliacao_brasil.csv` | 2 | Comparação combustível x modelo, Brasil, nos meses presentes nas duas bases. |
| `conciliacao_uf.csv` | 54 | Idem, por UF. |
| `conciliacao_municipio.parquet` | 11.147 | Idem, por município. |
| `qualidade_combustivel.csv` | 76 | Arquivos mensais da base por combustível: linhas, total, ajustes e inclusão na série. |
| `qualidade_modelo.csv` | 2 | Idem para a base por modelo. |

CSV: separador `;`, decimal `,`, UTF-8 com BOM (abre direto no Excel pt-BR). Parquet: ler com `pandas.read_parquet` ou no Power BI/R/DuckDB.
Colunas, tipos, fontes e classes: [DICIONARIO.md](DICIONARIO.md). Limitações e método de conciliação: README do repositório.
