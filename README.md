# eletromobilidade

Tratamento da base de frota de veículos da SENATRAN (RENAVAM) e construção de
uma base específica de eletromobilidade, por município, UF e Brasil, mês a mês.

## Fontes de dados

| Fonte (`--fontes`) | Onde | Tabelas usadas |
|---|---|---|
| `ckan` | API CKAN do [portal de dados abertos](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907), conjunto RENAVAM | `marca_modelo` (zip mensal) |
| `portal` | Páginas anuais [`frota-de-veiculos-{ano}`](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2025) do gov.br | `combustivel`, `municipio_tipo`, `uf_tipo` |

Tabelas reconhecidas (`--tabela`):

| Tabela | Arquivo da SENATRAN | Colunas |
|---|---|---|
| `marca_modelo` | Frota por UF, Município, Marca e Modelo, Ano | UF, Município, Marca Modelo, Ano Fabricação Veículo CRV, Qtd. Veículos |
| `combustivel` | Frota por UF, Município e Combustível | UF, Município, Combustível Veículo, Qtd. Veículos |
| `municipio_tipo` | Frota por Município e Tipo | — |
| `uf_tipo` | Frota por UF e Tipo de Veículo | — |

Quando o mesmo mês aparece nas duas fontes, vale a primeira listada em
`--fontes` (padrão: `ckan portal`). Os nomes dos arquivos não são estáveis
(`copy_of_…`, `Maro` para "Março"), por isso a tabela e o período são inferidos
do nome e do título de cada recurso. A UF vem por extenso; o pacote acrescenta
sigla, código IBGE da UF e região.

**Atenção:** o arquivo `marca_modelo` não informa o combustível. O
processamento (`processar`) usa hoje apenas a tabela `combustivel`.

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
# 1. ver o que está publicado num ano (nas duas fontes)
eletromobilidade links --ano 2026

# 2. baixar (para data/raw/{tabela}/{ano}/)
eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 9
eletromobilidade baixar --tabela combustivel --anos 2025 2026

# 3. gerar a base (lê tudo em data/raw, grava em data/processed)
eletromobilidade -v processar
```

Se o download automático falhar (o leiaute do portal muda), baixe os `.xlsx`
manualmente para `data/raw/` mantendo o nome original — ou qualquer nome que
contenha "combustivel", o mês por extenso e o ano — e rode `processar`.
Também é possível passar arquivos específicos:
`eletromobilidade processar caminho/arquivo.xlsx`.

Uso como biblioteca:

```python
from eletromobilidade import pipeline

longo = pipeline.processar_arquivos(pipeline.localizar_arquivos("data/raw"))
base = pipeline.construir_base(longo)
base["eletromobilidade_uf"].query("uf_sigla == 'SP'")
```

## Saídas (`data/processed/`)

Cada tabela é gravada em Parquet e em CSV (`;` como separador, `,` decimal, UTF-8 com BOM — abre direto no Excel pt-BR).

| Tabela | Grão | Conteúdo |
|---|---|---|
| `frota_combustivel` | mês × município × rótulo de combustível | Base tratada completa (todos os combustíveis) |
| `eletromobilidade_longo` | idem | Apenas rótulos eletrificados |
| `eletromobilidade_municipio` | mês × município | Frota por classe, total, eletrificada, participação |
| `eletromobilidade_uf` | mês × UF | idem |
| `eletromobilidade_brasil` | mês | idem (inclui registros sem UF válida) |
| `combustiveis_classificados` | rótulo de combustível | Auditoria: classe atribuída, origem (tabela/regra), total de veículos |

Colunas dos painéis: `frota_eletrico`, `frota_hibrido_plug_in`, `frota_hibrido`,
`frota_celula_combustivel`, `frota_combustao`, `frota_sem_informacao`,
`frota_total`, `frota_eletrificada` (soma das quatro primeiras) e
`participacao_eletrificada = frota_eletrificada / frota_total`.

## Classificação dos combustíveis

A correspondência rótulo RENAVAM → classe está em
[`src/eletromobilidade/dados/combustiveis.csv`](src/eletromobilidade/dados/combustiveis.csv)
e pode ser editada ou substituída (`--tabela-combustiveis`). Rótulos que não
constam da tabela são classificados por regra textual e aparecem com
`origem_classificacao = "regra"` na auditoria; a CLI emite um aviso listando-os.

| Classe | Rótulos (exemplos) |
|---|---|
| `eletrico` | ELETRICO/FONTE EXTERNA, ELETRICO/FONTE INTERNA |
| `hibrido_plug_in` | HIBRIDO PLUG-IN |
| `hibrido` | GASOLINA/ELETRICO, GASOLINA/ALCOOL/ELETRICO, DIESEL/ELETRICO |
| `celula_combustivel` | CELULA COMBUSTIVEL, HIDROGENIO (se aparecerem) |
| `combustao` | GASOLINA, ALCOOL/GASOLINA, DIESEL, GNV… |
| `sem_informacao` | SEM INFORMACAO, NAO IDENTIFICADO, VIDE/CAMPO/OBSERVACAO |

### Limitações conhecidas

1. **Tipo de veículo.** O arquivo por combustível não traz o tipo (automóvel,
   motocicleta, ônibus, caminhão). A `participacao_eletrificada` é, portanto,
   sobre a frota total registrada, não sobre veículos leves.
2. **"Fonte interna" vs. "fonte externa".** Os códigos 06 (ELETRICO/FONTE
   INTERNA) e 07 (ELETRICO/FONTE EXTERNA) vêm de uma tabela antiga do RENAVAM e
   seu significado operacional não está documentado de forma inequívoca na
   documentação pública consultada. Ambos são tratados como `eletrico`; o rótulo
   original é preservado em `frota_combustivel` para quem quiser separá-los.
3. **Híbridos plug-in.** O rótulo HIBRIDO PLUG-IN só aparece nos dados mais
   recentes; antes disso, PHEVs provavelmente foram registrados como
   GASOLINA/ELETRICO ou ELETRICO/FONTE EXTERNA. Séries longas de
   `frota_hibrido_plug_in` não devem ser lidas como série de vendas de PHEV.
4. **Frota registrada ≠ frota circulante.** A base do RENAVAM inclui veículos
   que já não circulam e não foram baixados.

## Testes

```bash
pytest
```

Os testes usam arquivos sintéticos no leiaute da SENATRAN (`tests/conftest.py`).

## Próximos passos

- Código IBGE do município (junção por nome normalizado + UF com a tabela do IBGE).
- Cruzamento com "Frota por Município e Tipo" e com a base por marca/modelo para
  isolar veículos leves.
- Validação contra séries publicadas (ABVE, ANFAVEA).
