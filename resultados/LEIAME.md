# Resultados

Gerado por `eletromobilidade publicar` a partir de `data/processed` em 2026-10-13 19:27 UTC (código no commit `1db9509`). Não edite à mão: rode `processar` e `publicar` de novo.

## Cobertura

- **Base por combustível:** jun/2020 a set/2026, 75 meses; faltam jan/2022.
- **Base por modelo:** 1 mês (set/2026).
- **Conciliação:** 1 mês (set/2026).
- Ajuste em d_frota_por_uf_municipio_combustivel_novembro_2021.xlsx (nov/2021): contagens divididas por 10 (todas eram múltiplas de 10 no arquivo publicado).
- Ajuste em d_frota_por_uf_municipio_combustivel_janeiro_2022.xlsx (jan/2022): idêntico a 2021-12; excluído da série.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---:|---|
| `combustivel_brasil.csv` | 75 | Base por combustível: frota por classe, total, eletrificada e participação, Brasil, por mês. |
| `combustivel_uf.csv` | 2.025 | Idem, por UF. |
| `combustivel_municipio.parquet` | 417.997 | Idem, por município. |
| `combustivel_eletrificados.parquet` | 725.874 | Base por combustível: rótulos eletrificados por município e mês. |
| `combustiveis_classificados.csv` | 30 | Auditoria: rótulos de combustível, classe atribuída e total de veículos. |
| `modelo_brasil.csv` | 1 | Base por modelo: frota por classe (inclui plug-in x convencional e híbrido leve), Brasil, por mês. |
| `modelo_uf.csv` | 27 | Idem, por UF. |
| `modelo_municipio.parquet` | 5.574 | Idem, por município. |
| `modelo_eletrificados.parquet` | 181.737 | Base por modelo: eletrificados e híbridos leves por município, modelo e ano de fabricação. |
| `modelos_classificados.parquet` | 40.548 | Auditoria: cada modelo, classe, regra aplicada, total e marcação 'revisar'. |
| `conciliacao_brasil.csv` | 1 | Comparação combustível x modelo, Brasil, nos meses presentes nas duas bases. |
| `conciliacao_uf.csv` | 27 | Idem, por UF. |
| `conciliacao_municipio.parquet` | 5.574 | Idem, por município. |
| `qualidade_combustivel.csv` | 76 | Arquivos mensais da base por combustível: linhas, total, ajustes e inclusão na série. |
| `qualidade_modelo.csv` | 1 | Idem para a base por modelo. |

CSV: separador `;`, decimal `,`, UTF-8 com BOM (abre direto no Excel pt-BR). Parquet: ler com `pandas.read_parquet` ou no Power BI/R/DuckDB.
Colunas, tipos, fontes e classes: [DICIONARIO.md](DICIONARIO.md). Limitações e método de conciliação: README do repositório.
