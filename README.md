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

| Fonte (`--fontes`) | Onde | O que tem |
|---|---|---|
| `ckan` | API CKAN do [portal de dados abertos](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907), conjunto RENAVAM | Só `marca_modelo`, zip mensal desde 2013 (até 2015 parte em `.rar`, não suportado) |
| `portal` | Páginas anuais [`frota-de-veiculos-{ano}`](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026) do gov.br | Oito tabelas mensais em `.xlsx` (abaixo) |

Tabelas reconhecidas (`--tabela`), conforme verificado no portal em outubro/2026:

| Tabela | Arquivo da SENATRAN | Usada no processamento |
|---|---|---|
| `marca_modelo` | `I_` Frota por UF, Município, Marca e Modelo, Ano (CKAN) | sim (base por modelo) |
| `combustivel` | `D_` Frota por UF, Município e Combustível | sim (base por combustível) |
| `municipio_tipo` | Frota por Município e Tipo | não (próximo passo) |
| `uf_tipo` | Frota por UF e Tipo de Veículo | não |
| `ano_fabricacao` | `F_` Frota por UF, Município, Ano de Fabricação e Ano Modelo | não |
| `tipo_especie_eixos` | `G_` Frota por UF, Município, Tipo, Espécie e Eixos | não |
| `potencia` | `E_` Frota por UF, Município e Potência | não |
| `restricao`, `cor`, `cep` | `H_`, `C_`, `A_` | não |

Quando o mesmo mês aparece nas duas fontes, vale a primeira listada em
`--fontes` (padrão: `ckan portal`). Os servidores do gov.br são instáveis
(503, conexões que caem no meio de downloads de 137 MB): as requisições são
repetidas com espera exponencial e downloads interrompidos são retomados do
ponto em que pararam (HTTP `Range`). Os nomes dos arquivos não são estáveis
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

Os agregados mensais da base por modelo ficam em cache (`data/interim/marca_modelo/`,
opção `--cache`): ao acrescentar meses à série, só os novos são lidos. Mudar as
regras de `dados/modelos.csv` invalida o cache automaticamente. Tabelas com mais
linhas que o Excel suporta (ex.: `frota_combustivel` com a série completa) são
gravadas só em Parquet.

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
| `qualidade_{combustivel,modelo}` | arquivo mensal | Linhas, frota total, ajustes aplicados e se o mês entrou na série |

Os painéis trazem `frota_<classe>` para cada classe, `frota_total`,
`frota_eletrificada` e `participacao_eletrificada = frota_eletrificada / frota_total`.
O painel do Brasil inclui registros sem UF válida; o de UF, não.

## Série histórica e qualidade dos arquivos

Disponibilidade verificada em outubro/2026: o arquivo por combustível existe de
janeiro/2019 a setembro/2026 (faltam janeiro a maio/2020 no portal); o de
marca/modelo, de 2019 em diante no CKAN (e alguns meses de 2013, 2014 e 2018).

Defeitos encontrados nos arquivos publicados e tratados automaticamente
(`qualidade.py`, registrados em `qualidade_*`):

| Arquivo | Defeito | Tratamento |
|---|---|---|
| Combustível, nov/2021 | Todas as contagens multiplicadas por 10 (frota de 1,135 bilhão) | Contagens divididas por 10 (113,5 milhões, coerente com out e dez/2021) |
| Combustível, jan/2022 | Idêntico ao de dez/2021 | Mês excluído da série |
| Combustível, ago/2019 | Acentos corrompidos ("MunicÃ­pio") e linha extra "Column1…" | Texto reparado na leitura |
| Combustível, jan/2019 | Nome com "janeito" | Mês reconhecido |

A regra de escala só age quando *todas* as contagens positivas de um arquivo
(milhares) são múltiplas de 10, o que não ocorre em dado real. Na coleta, a
API do CKAN e os downloads respondem 503 com frequência: a listagem de recursos
fica guardada em `data/raw/ckan_renavam.json` e é usada quando a API cai; uma
fonte com 3 falhas seguidas é deixada para a execução seguinte, sem interromper
as demais.

## Classificação dos combustíveis

A correspondência rótulo RENAVAM → classe está em
[`src/eletromobilidade/dados/combustiveis.csv`](src/eletromobilidade/dados/combustiveis.csv)
e pode ser editada ou substituída (`--tabela-combustiveis`). Rótulos que não
constam da tabela são classificados por regra textual e aparecem com
`origem_classificacao = "regra"` na auditoria; a CLI emite um aviso listando-os.

Rótulos encontrados no arquivo de setembro/2026 (136,4 milhões de veículos):

| Classe | Rótulo RENAVAM | Veículos (set/2026) |
|---|---|---:|
| `eletrico` | ELETRICO/FONTE EXTERNA | 391.095 |
| | ELETRICO/FONTE INTERNA | 53.093 |
| | ELETRICO | 40.219 |
| `hibrido_plug_in` | HIBRIDO PLUG-IN | 83.987 |
| `hibrido` | GASOLINA/ELETRICO | 408.068 |
| | GASOLINA/ALCOOL/ELETRICO | 299.481 |
| | HIBRIDO | 41.033 |
| | DIESEL/ELETRICO | 13.710 |
| | ETANOL/ELETRICO, HIBRIDO/GAS NATURAL VEICULAR | 4 |
| `celula_combustivel` | CELULA COMBUSTIVEL | 13 |
| `combustao` | ALCOOL/GASOLINA, GASOLINA, DIESEL, ALCOOL, combinações com GNV… | 130,1 milhões |
| `sem_informacao` | Sem Informação, VIDE/CAMPO/OBSERVACAO, Não Identificado, Não se Aplica | 4,96 milhões |

**Plug-in vs. híbrido convencional.** `hibrido_plug_in` (PHEV) recarrega na
tomada; `hibrido` (HEV) só recarrega a bateria pelo motor a combustão e pela
frenagem regenerativa. Na base por modelo a separação é feita pelo nome
(PHEV, DM, T8, 4xe, 330e…). Na base por combustível ela é parcial: só o rótulo
HIBRIDO PLUG-IN identifica PHEV com segurança; GASOLINA/ELETRICO e HIBRIDO podem
conter PHEV (limitação 3) e os rótulos X/ELETRICO podem conter híbridos leves
(limitação 5). A conciliação compara as duas parcelas separadamente e somadas.

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
`total`, `eletrico`, `hibrido_plug_in`, `hibrido`, `hibridos` (soma dos dois) e
`eletrificada`, com
`_combustivel`, `_modelo`, `_diferenca` (modelo − combustível) e `_razao`
(modelo / combustível); mais `hibrido_leve_modelo`. Leitura:

- `total_diferenca ≠ 0`: os dois arquivos não cobrem o mesmo universo
  (verificar antes de interpretar o resto).
- `eletrico_razao < 1`: modelos elétricos sem regra (falso negativo).
  `> 1`: regra capturando modelo a combustão (falso positivo).
- `hibrido_plug_in` e `hibrido`: comparar com cautela (limitações 3 e 5);
  a soma `hibridos` é mais comparável entre as bases.

### Resultado com dados reais (setembro/2026)

Conciliação com os dois arquivos do mesmo mês, depois da calibração das regras
(arquivo de marca/modelo: 22 milhões de linhas, 40,5 mil modelos distintos,
processado em 1,5 min):

| Indicador (UFs válidas) | Combustível | Modelo | Modelo / combustível |
|---|---:|---:|---:|
| Frota total (Brasil) | 136.424.856 | 136.424.856 | 1,000 |
| Elétrico | 395.132 | 379.826 | 0,961 |
| Híbrido plug-in | 79.245 | 352.706 | 4,45 |
| Híbrido convencional | 709.697 | 260.628 | 0,37 |
| Híbridos, soma | 788.942 | 613.334 | 0,78 |
| Híbridos + híbridos leves do modelo | 788.942 | 730.941 | 0,93 |

Leitura:

- A frota total coincide em todas as UFs: os dois arquivos cobrem o mesmo
  universo.
- Elétricos: a base por modelo recupera 96,1% nas UFs válidas (de 93% a
  99,6% por UF) e 91,9% no Brasil. O resíduo maior está no grupo de
  UF/município "Sem Informação" (3,1 milhões de veículos, quase todos sem ano
  de fabricação).
- **O campo combustível não separa plug-in de híbrido convencional.** A base
  por modelo tem 4,5 vezes mais plug-ins que o rótulo HIBRIDO PLUG-IN: a maior
  parte dos PHEV está registrada como GASOLINA/ELETRICO ou similar. Para a
  separação PHEV × HEV, usar a base por modelo.
- **O campo combustível conta híbridos leves como híbridos.** Somando os
  híbridos leves da base por modelo, os híbridos fecham em 93%. Como a decisão
  do projeto é excluir híbridos leves, a base por combustível superestima a
  frota híbrida.

Classificações confirmadas por conhecimento de mercado (não pelo texto):
Shineray PT2/PT3/PT4/PT7 e SE1/SE2/SE3 são elétricos; GAC GS4 é híbrido
convencional a gasolina.

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
5. **Híbridos leves no campo combustível.** Híbridos leves flex (ex.: Fiat
   "Hybrid" 12 V) podem estar registrados como GASOLINA/ALCOOL/ELETRICO e
   entrar em `hibrido` na base por combustível, enquanto na base por modelo
   ficam fora (`hibrido_leve`). A conciliação (`hibrido_diferenca` vs.
   `hibrido_leve_modelo`) mede esse efeito.
6. **Regras por nome de modelo.** Algumas classificações dependem de
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

- Estender a série a outros meses e acompanhar a lista `revisar` a cada mês novo.
- Código IBGE do município (junção por nome normalizado + UF com a tabela do IBGE).
- Cruzamento com "Frota por Município e Tipo" para isolar veículos leves.
- Validação contra séries publicadas (ABVE, ANFAVEA).
