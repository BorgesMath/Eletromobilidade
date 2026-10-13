# eletromobilidade

Tratamento da base de frota de veículos da SENATRAN (RENAVAM) e construção de
uma base específica de eletromobilidade, por município, UF e Brasil, mês a mês.

São duas bases, construídas por caminhos independentes e depois conciliadas:

| Base | Arquivo de origem | Como a tecnologia é obtida | Para que serve |
|---|---|---|---|
| **combustível** | Frota por UF, Município e Combustível | Campo combustível do RENAVAM | Contagem oficial de eletrificados por município |
| **modelo** | Frota por UF, Município, Marca e Modelo, Ano | Inferida do nome do modelo (regras) | Detalhe por modelo, marca e ano de fabricação |
| **conciliação** | as duas | Comparação mês × recorte | Mede o erro da classificação por modelo |

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

**Atenção:** o arquivo `marca_modelo` não informa o combustível; por isso a
tecnologia é inferida do nome do modelo (ver abaixo).

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

# 3. gerar as bases (lê tudo em data/raw, grava em data/processed)
eletromobilidade -v processar
```

`processar` monta a base por combustível se houver arquivos de combustível, a
base por modelo se houver arquivos de marca/modelo e a conciliação para os meses
presentes nas duas. A tabela de cada arquivo é reconhecida pelo nome
("combustivel" ou "marca"/"modelo"), e o período pelo mês por extenso e o ano.
Se o download automático falhar, baixe os arquivos manualmente para `data/raw/`
mantendo o nome original, ou passe arquivos específicos:
`eletromobilidade processar arquivo1.xlsx arquivo2.zip`.

O arquivo de marca/modelo é lido em blocos de 1 milhão de linhas. Em teste com
7,5 milhões de linhas (amostra real replicada), levou 29 s com pico de 650 MB
de memória; um mês completo (~22 milhões de linhas) deve levar cerca de 1,5 min.

Uso como biblioteca:

```python
from eletromobilidade import pipeline
from eletromobilidade.base_modelo import processar_arquivos_modelo
from eletromobilidade.conciliacao import conciliar_bases

longo = pipeline.processar_arquivos(pipeline.localizar_arquivos("data/raw", "combustivel"))
tabelas = pipeline.construir_base_combustivel(longo)
tabelas |= processar_arquivos_modelo(pipeline.localizar_arquivos("data/raw", "marca_modelo"))
tabelas |= conciliar_bases(tabelas)
tabelas["conciliacao_uf"].query("uf_sigla == 'SP'")
```

## Saídas (`data/processed/`)

Cada tabela é gravada em Parquet e em CSV (`;` como separador, `,` decimal, UTF-8 com BOM — abre direto no Excel pt-BR).

| Tabela | Grão | Conteúdo |
|---|---|---|
| `frota_combustivel` | mês × município × rótulo de combustível | Base por combustível completa (todos os combustíveis) |
| `combustivel_eletrificados` | idem | Apenas rótulos eletrificados |
| `combustivel_{municipio,uf,brasil}` | mês × recorte | Painel da base por combustível |
| `combustiveis_classificados` | rótulo de combustível | Auditoria: classe, origem (tabela/regra), total |
| `modelo_eletrificados` | mês × município × modelo × ano de fabricação | Modelos eletrificados e híbridos leves |
| `modelo_{municipio,uf,brasil}` | mês × recorte | Painel da base por modelo |
| `modelos_classificados` | mês × modelo | Auditoria: classe, regra aplicada, total, `revisar` |
| `conciliacao_{municipio,uf,brasil}` | mês × recorte | Comparação entre as duas bases |

Os painéis trazem `frota_<classe>` para cada classe, `frota_total`,
`frota_eletrificada` e `participacao_eletrificada = frota_eletrificada / frota_total`.
O painel do Brasil inclui registros sem UF válida; o de UF, não.

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

## Classificação por modelo

O texto "Marca Modelo" (ex.: `I/BYD DOLPHIN GS 180EV`, `I/GWM HAVAL H6 PHEV19`,
`TOYOTA/COROLLA ALTIS HV`) é classificado por regras ordenadas em
[`src/eletromobilidade/dados/modelos.csv`](src/eletromobilidade/dados/modelos.csv)
(`classe;padrao;nota`, separador `;`, editável ou substituível por
`--regras-modelos`). A primeira regra cujo padrão (regex sobre o texto sem
acentos, em caixa alta) casa define a classe; sem regra, `combustao`. O número da
regra aplicada fica registrado em `modelos_classificados`.

| Classe | Exemplos reais | Entra em `frota_eletrificada` |
|---|---|---|
| `eletrico` | BYD Dolphin, Tesla, Volvo EX30, Renault E-Kwid, Peugeot E-Expert | sim |
| `hibrido_plug_in` | BYD Song/King DM, Haval H6 PHEV/GT, Volvo T8, BMW 330e, Jeep 4xe | sim |
| `hibrido` | Corolla/Corolla Cross Hybrid, Lexus ES300h, Haval H6 HEV | sim |
| `celula_combustivel` | Mirai (se aparecer) | sim |
| `hibrido_leve` | Fiat Pulse/Fastback Hybrid (12 V), Kia Sportage MHEV | **não** (coluna própria) |
| `combustao` | demais | não |
| `nao_motorizado` | reboques (`R/`) e semirreboques (`SR/`) | não |

As regras por marca vêm antes das genéricas porque os nomes têm armadilhas,
cobertas por testes: `VW/8.150E DELIVERY` (diesel, "E" de eletrônico),
`VW/POLO 1.6 E-FLEX` (flex), `HYUNDAI/HB20 EVOLUTION` e `CHEV/…` (contêm "EV"/"HEV"),
`TOYOTA/YCROSS XRE-HYBRID` (híbrido convencional, não plug-in).

A coluna `revisar` marca modelos de marcas com linha (quase) toda eletrificada
(BYD, GWM, GAC, Omoda/Jaecoo, Zeekr…) que não casaram com nenhuma regra. A CLI
lista esses casos ao final.

## Conciliação

Para cada mês presente nas duas bases e cada recorte (Brasil, UF, município):
`total`, `eletrico`, `hibridos` (plug-in + convencional) e `eletrificada`, com
`_combustivel`, `_modelo`, `_diferenca` (modelo − combustível) e `_razao`
(modelo / combustível); mais `hibrido_leve_modelo`. Leitura:

- `total_diferenca ≠ 0`: os dois arquivos não cobrem o mesmo universo
  (verificar antes de interpretar o resto).
- `eletrico_razao < 1`: modelos elétricos sem regra (falso negativo).
  `> 1`: regra capturando modelo a combustão (falso positivo).
- `hibridos`: comparar com cautela, ver limitação 3.

## Limitações conhecidas

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
5. **Regras por nome de modelo.** Algumas classificações dependem de
   conhecimento de mercado, não do texto: "Hybrid" da Stellantis e da Caoa
   Chery como híbrido leve; Audi "HIBRIDO" (pode ser híbrido leve 48 V) como
   híbrido; Jaecoo 7 como plug-in; BYD sem "DM" como elétrico. Cada caso está
   anotado na coluna `nota` das regras, e a conciliação mede o efeito agregado.

## Testes

```bash
pytest
```

Os testes usam arquivos sintéticos no leiaute da SENATRAN (`tests/conftest.py`)
e, para o classificador por modelo, textos reais do campo "Marca Modelo".

## Próximos passos

- Rodar com os arquivos reais do mesmo mês e ajustar as regras pela conciliação.
- Código IBGE do município (junção por nome normalizado + UF com a tabela do IBGE).
- Cruzamento com "Frota por Município e Tipo" para isolar veículos leves.
- Validação contra séries publicadas (ABVE, ANFAVEA).
