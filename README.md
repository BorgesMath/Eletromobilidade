# eletromobilidade

Tratamento da base de frota de veículos da SENATRAN (RENAVAM) e construção de
uma base específica de eletromobilidade, por município, UF e Brasil, mês a mês.

## Fonte de dados

SENATRAN / Ministério dos Transportes, página anual
[Frota de Veículos](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2025)
(`frota-de-veiculos-{ano}`). O arquivo usado é **Frota por UF, Município e
Combustível** (mensal, `.xlsx`), com as colunas:

| UF | Município | Combustível Veículo | Qtd. Veículos |
|----|-----------|---------------------|---------------|
| SAO PAULO | SAO PAULO | ELETRICO/FONTE EXTERNA | … |

A UF vem por extenso; o pacote acrescenta sigla, código IBGE da UF e região.
Os nomes dos arquivos no portal não são estáveis (`copy_of_…`, `Maro` para
"Março"), por isso o período é inferido do nome/texto do link.

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
# 1. ver o que está publicado num ano
eletromobilidade links --ano 2025

# 2. baixar os arquivos de combustível (para data/raw/AAAA/)
eletromobilidade baixar --anos 2025 2026
eletromobilidade baixar --anos 2026 --meses 1 2 3

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
