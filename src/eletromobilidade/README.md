# O pacote `eletromobilidade`

Coleta os arquivos da SENATRAN, monta as duas bases (por combustível e por
modelo), concilia uma com a outra e publica em `resultados/`. As regras e
tabelas de referência que o pacote lê estão em [`dados/`](dados/README.md).

## Módulos

| Módulo | O que faz |
|---|---|
| `cli.py` | Linha de comando (`eletromobilidade …`) |
| `coleta.py` | Descoberta e download dos arquivos da SENATRAN no CKAN e no gov.br |
| `leitura.py` | Leitura e padronização dos arquivos mensais (`.xlsx`, `.zip`, `.csv`) |
| `qualidade.py` | Defeitos conhecidos dos arquivos publicados e o registro de cada mês |
| `pipeline.py` | Base por combustível: série longa, painéis por município, UF e Brasil |
| `classificacao.py` | Rótulo de combustível do RENAVAM → classe |
| `base_modelo.py` | Base por modelo, lida em blocos, com cache mensal |
| `modelos.py` | Texto "Marca Modelo" → classe e marca |
| `tipos.py` | Tipo de veículo dos modelos eletrificados |
| `inmetro.py` | Extração e junção da tabela PBE Veicular |
| `municipios.py` | Código IBGE do município e dimensão de município |
| `populacao.py` | Estimativas de população do IBGE por município e mês |
| `conciliacao.py` | Comparação entre as duas bases |
| `publicacao.py` | Cópia para `resultados/` e geração do `LEIAME.md` e do `DICIONARIO.md` |
| `texto.py`, `ufs.py` | Normalização de texto e tabela de UFs |

## Linha de comando

```bash
# 1. ver o que está publicado num ano (nas duas fontes)
eletromobilidade links --ano 2026

# 2. baixar (para data/raw/{tabela}/{ano}/)
eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 9
eletromobilidade baixar --tabela combustivel --anos 2025 2026

# 3. gerar as bases (lê tudo em data/raw, grava em data/processed)
eletromobilidade -v processar

# 4. publicar painéis, conciliação e auditorias em resultados/ (versionado)
eletromobilidade publicar

# extrair a tabela PBE Veicular do Inmetro de um PDF de ciclo (só quando sai ciclo novo)
eletromobilidade pbev tabela-pbev-2026.pdf --ciclo 2026

# atualizar a lista de municípios do IBGE (só quando o IBGE cria ou renomeia município)
eletromobilidade municipios

# atualizar as estimativas de população (uma vez por ano, quando o IBGE publica, em agosto)
eletromobilidade populacao
```

Opções de `processar`: `--desde` (padrão `2020-01`; `--desde ''` usa todos os
arquivos baixados), `--ate`, `--tabela-combustiveis` e `--regras-modelos` (CSVs
alternativos às tabelas de `dados/`), `--sem-csv`, `--cache` e `--sem-cache`.

`processar` monta a base por combustível se houver arquivos de combustível, a
base por modelo se houver arquivos de marca/modelo e a conciliação para os meses
presentes nas duas. A tabela de cada arquivo é reconhecida pelo nome
("combustivel" ou "marca"/"modelo"), e o período pelo mês por extenso e o ano.
Se o download automático falhar, baixe os arquivos manualmente para `data/raw/`
mantendo o nome original, ou passe arquivos específicos:
`eletromobilidade processar arquivo1.xlsx arquivo2.zip`.

Depois de mudar uma regra ou tabela de `dados/`, as tabelas de `resultados/`
ficam defasadas até rodar `processar` e `publicar` de novo, o que exige os
arquivos da SENATRAN em `data/raw/`.

## Uso como biblioteca

```python
from eletromobilidade import pipeline
from eletromobilidade.base_modelo import processar_arquivos_modelo
from eletromobilidade.conciliacao import conciliar_bases
from eletromobilidade.municipios import dimensao_municipio

longo = pipeline.processar_arquivos(pipeline.localizar_arquivos("data/raw", "combustivel"))
tabelas = pipeline.construir_base_combustivel(longo)
tabelas |= processar_arquivos_modelo(pipeline.localizar_arquivos("data/raw", "marca_modelo"))
tabelas |= conciliar_bases(tabelas)
tabelas["municipios_dimensao"] = dimensao_municipio([tabelas["combustivel_municipio"],
                                                     tabelas["modelo_municipio"]])
tabelas["conciliacao_uf"].query("uf_sigla == 'SP'")
```

## Coleta

| Fonte (`--fontes`) | Onde | O que tem |
|---|---|---|
| `ckan` | API CKAN do [portal de dados abertos](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907), conjunto RENAVAM | Só `marca_modelo`, zip mensal desde 2013 (até 2015 parte em `.rar`, não suportado) |
| `portal` | Páginas anuais [`frota-de-veiculos-{ano}`](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026) do gov.br | Oito tabelas mensais em `.xlsx` (abaixo) |

Tabelas reconhecidas (`--tabela`), conforme verificado no portal em outubro/2026:

| Tabela | Arquivo da SENATRAN | Usada no processamento |
|---|---|---|
| `marca_modelo` | `I_` Frota por UF, Município, Marca e Modelo, Ano (CKAN) | sim (base por modelo) |
| `combustivel` | `D_` Frota por UF, Município e Combustível | sim (base por combustível) |
| `municipio_tipo` | Frota por Município e Tipo | não |
| `uf_tipo` | Frota por UF e Tipo de Veículo | não |
| `ano_fabricacao` | `F_` Frota por UF, Município, Ano de Fabricação e Ano Modelo | não |
| `tipo_especie_eixos` | `G_` Frota por UF, Município, Tipo, Espécie e Eixos | não |
| `potencia` | `E_` Frota por UF, Município e Potência | não |
| `restricao`, `cor`, `cep` | `H_`, `C_`, `A_` | não |

Quando o mesmo mês aparece nas duas fontes, vale a primeira listada em
`--fontes` (padrão: `ckan portal`). Os servidores do gov.br são instáveis (503,
conexões que caem no meio de downloads de 137 MB): as requisições são repetidas
com espera exponencial, e downloads interrompidos são retomados do ponto em que
pararam (HTTP `Range`). A listagem de recursos do CKAN fica guardada em
`data/raw/ckan_renavam.json` e é usada quando a API cai; uma fonte com 3 falhas
seguidas é deixada para a execução seguinte, sem interromper as demais.

Os nomes dos arquivos não são estáveis (`copy_of_…`, `Maro` para "Março"), por
isso a tabela e o período são inferidos do nome e do título de cada recurso. A
UF vem por extenso; o pacote acrescenta sigla, código IBGE da UF e região. O
município vem só pelo nome; o pacote acrescenta o código IBGE
([`dados/`](dados/README.md#município)).

## Série histórica e qualidade dos arquivos

Disponibilidade verificada em outubro/2026: o arquivo por combustível existe em
2013 (6 meses), 2014, 2016 (6 meses), 2017, 2018 e de janeiro/2019 em diante
(faltam janeiro a maio/2020); o de marca/modelo, de 2019 em diante no CKAN (e
alguns meses de 2013, 2014 e 2018, parte em `.rar`).

Defeitos encontrados nos arquivos publicados e tratados automaticamente
(`qualidade.py`, registrados em `qualidade_*`):

| Arquivo | Defeito | Tratamento |
|---|---|---|
| Combustível, nov/2021 | Todas as contagens multiplicadas por 10 (frota de 1,135 bilhão) | Contagens divididas por 10 (113,5 milhões, coerente com out e dez/2021) |
| Combustível, jan/2022 | Idêntico ao de dez/2021 | Mês excluído da série |
| Combustível, ago/2019 | Acentos corrompidos ("MunicÃ­pio") e linha extra "Column1…" | Texto reparado na leitura |
| Combustível, jan/2019 | Nome com "janeito" | Mês reconhecido |

A regra de escala só age quando *todas* as contagens positivas de um arquivo
(milhares) são múltiplas de 10, o que não ocorre em dado real.

## Desempenho e cache

O arquivo de marca/modelo é lido em blocos de 1 milhão de linhas; um mês completo
(~22 milhões de linhas, ~130 MB) leva cerca de 1,5 min. Os agregados mensais da
base por modelo ficam em cache (`data/interim/marca_modelo/`, opção `--cache`):
ao acrescentar meses, só os novos são lidos, e mudar as regras de
`dados/modelos.csv` invalida o cache automaticamente. Uma rodada completa de
`processar` (76 meses de combustível e 2 de marca/modelo) leva perto de 10 min.

## Saídas (`data/processed/`)

Cada tabela é gravada em Parquet e em CSV (`;` como separador, `,` decimal,
UTF-8 com BOM, que abre direto no Excel pt-BR). Tabelas com mais linhas que o
Excel suporta (ex.: `frota_combustivel` com a série completa) ficam só em
Parquet. `publicar` copia para `resultados/` as que vão para o repositório.

| Tabela | Grão | Conteúdo |
|---|---|---|
| `frota_combustivel` | mês × município × rótulo de combustível | Base por combustível completa (todos os combustíveis) |
| `combustivel_eletrificados` | idem | Apenas rótulos eletrificados |
| `combustivel_{municipio,uf,brasil}` | mês × recorte | Painel da base por combustível |
| `combustiveis_classificados` | rótulo de combustível | Auditoria: classe, origem (tabela/regra), total |
| `modelo_eletrificados` | mês × município × modelo × ano de fabricação | Modelos eletrificados e híbridos leves |
| `modelo_{municipio,uf,brasil}` | mês × recorte | Painel da base por modelo |
| `modelo_tipo_{uf,brasil}` | mês × recorte × tipo de veículo | Eletrificados e híbridos leves por tipo, com a parte de cada tipo |
| `modelos_classificados` | mês × modelo | Auditoria: classe, regra aplicada, total, `revisar`, marca, PBE, tipo |
| `modelos_dimensao` | modelo | Dimensão de modelo: grafia do RENAVAM, marca canônica, origem |
| `conciliacao_{municipio,uf,brasil}` | mês × recorte | Comparação entre as duas bases |
| `qualidade_{combustivel,modelo}` | arquivo mensal | Linhas, frota total, ajustes aplicados e se o mês entrou na série |
| `municipios_dimensao` | município (código IBGE) | Nome oficial, UF, região e as grafias com que a SENATRAN publicou o município |

Os painéis trazem `frota_<classe>` para cada classe, `frota_total`,
`frota_eletrificada` e `participacao_eletrificada = frota_eletrificada / frota_total`.
O painel do Brasil inclui registros sem UF válida; o de UF, não. Toda tabela no
grão de município traz `cod_municipio_ibge`. Os painéis da base por combustível
trazem também `populacao`, `ano_populacao` e `eletrificada_por_mil_habitantes`.
Colunas e tipos de cada tabela publicada:
[`resultados/DICIONARIO.md`](../../resultados/DICIONARIO.md).

## Conciliação

Para cada mês presente nas duas bases e cada recorte (Brasil, UF, município):
`total`, `eletrico`, `hibrido_plug_in`, `hibrido`, `hibridos` (soma dos dois) e
`eletrificada`, com `_combustivel`, `_modelo`, `_diferenca` (modelo −
combustível) e `_razao` (modelo / combustível); mais `hibrido_leve_modelo`.
Leitura:

- `total_diferenca ≠ 0`: os dois arquivos não cobrem o mesmo universo
  (verificar antes de interpretar o resto). Em set/2026 a frota total coincide
  em todas as UFs.
- `eletrico_razao < 1`: modelos elétricos sem regra (falso negativo). `> 1`:
  regra capturando modelo a combustão (falso positivo).
- `hibrido_plug_in` e `hibrido` não se comparam um a um: o campo combustível
  registra a maior parte dos plug-ins como GASOLINA/ELETRICO e conta o híbrido
  leve como híbrido. A soma `hibridos`, e ela mais `hibrido_leve_modelo`, é o
  que se compara.

Teste das regras num mês antigo (dez/2019, regras calibradas em 2026): frota
total idêntica; elétricos 4.462 pelo modelo contra 4.367 pelo combustível
(102%); híbridos em 96,6%. O teste é anterior à correção dos BMW com código de
motor EV (21/10/2026), e os 102% provavelmente incluem esses falsos elétricos:
em dez/2020 a mesma correção derrubou o reconhecimento de elétricos nas UFs
válidas de 99% para 61%. Em 2019 o rótulo HIBRIDO PLUG-IN não existia: os 2.442
plug-ins identificados pelo nome estão, no campo combustível, entre os híbridos.
