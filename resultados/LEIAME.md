# Resultados

Gerado por `eletromobilidade publicar` a partir de `data/processed` em 2026-10-13 19:06 UTC (código no commit `2242045`). Não edite à mão: rode `processar` e `publicar` de novo.

## Cobertura

- **Base por combustível:** jan/2019 a set/2026, 87 meses; faltam jan/2020, fev/2020, mar/2020, abr/2020, mai/2020, jan/2022.
- **Base por modelo:** 2 meses (dez/2019, set/2026).
- **Conciliação:** 2 meses (dez/2019, set/2026).
- Ajuste em d_frota_por_uf_municipio_combustivel_novembro_2021.xlsx (nov/2021): contagens divididas por 10 (todas eram múltiplas de 10 no arquivo publicado).
- Ajuste em d_frota_por_uf_municipio_combustivel_janeiro_2022.xlsx (jan/2022): idêntico a 2021-12; excluído da série.

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---:|---|
| `combustivel_brasil.csv` | 87 | Base por combustível: frota por classe, total, eletrificada e participação, Brasil, por mês. |
| `combustivel_uf.csv` | 2.349 | Idem, por UF. |
| `combustivel_municipio.parquet` | 484.873 | Idem, por município. |
| `combustivel_eletrificados.parquet` | 748.017 | Base por combustível: rótulos eletrificados por município e mês. |
| `combustiveis_classificados.csv` | 30 | Auditoria: rótulos de combustível, classe atribuída e total de veículos. |
| `modelo_brasil.csv` | 2 | Base por modelo: frota por classe (inclui plug-in x convencional e híbrido leve), Brasil, por mês. |
| `modelo_uf.csv` | 54 | Idem, por UF. |
| `modelo_municipio.parquet` | 11.147 | Idem, por município. |
| `modelo_eletrificados.parquet` | 190.129 | Base por modelo: eletrificados e híbridos leves por município, modelo e ano de fabricação. |
| `modelos_classificados.parquet` | 69.756 | Auditoria: cada modelo, classe, regra aplicada, total e marcação 'revisar'. |
| `conciliacao_brasil.csv` | 2 | Comparação combustível x modelo, Brasil, nos meses presentes nas duas bases. |
| `conciliacao_uf.csv` | 54 | Idem, por UF. |
| `conciliacao_municipio.parquet` | 11.147 | Idem, por município. |
| `qualidade_combustivel.csv` | 88 | Arquivos mensais da base por combustível: linhas, total, ajustes e inclusão na série. |
| `qualidade_modelo.csv` | 2 | Idem para a base por modelo. |

CSV: separador `;`, decimal `,`, UTF-8 com BOM (abre direto no Excel pt-BR). Parquet: ler com `pandas.read_parquet` ou no Power BI/R/DuckDB.
Definições das classes, limitações e método de conciliação: ver o README do repositório.
