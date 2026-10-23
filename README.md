# eletromobilidade

Base de eletromobilidade a partir da frota de veículos da SENATRAN (RENAVAM),
por município, UF e Brasil, mês a mês — e o painel de Power BI construído sobre
ela.

O projeto tem três camadas, e a divisão entre elas é deliberada:

| Camada | Onde | O que faz |
|---|---|---|
| **Dados** | [`src/`](src/eletromobilidade), [`tests/`](tests) | Coleta, trata, classifica e concilia. É onde está a lógica e o teste automatizado. Publica [`resultados/`](resultados/LEIAME.md). |
| **Painel** | [`pbi/`](pbi/MODELO.md) | Modelo estrela, Power Query, DAX e tema. Lê só `resultados/` — nunca a SENATRAN direto. |
| **Roteiro** | [`docs/`](docs/ROTEIRO.md) | O que falta, em ordem de valor, e o que a base sustenta hoje. |

Nada de regra de negócio no Power BI: o que decide se um veículo é eletrificado
mora no Python, onde um teste pega a mudança. O PBI apresenta e agrega.

Comece por [`pbi/MODELO.md`](pbi/MODELO.md) se o assunto é o painel, por
[`docs/ROTEIRO.md`](docs/ROTEIRO.md) se é o que vem depois, e pelo resto deste
arquivo se é o tratamento dos dados.

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
sigla, código IBGE da UF e região. O município vem só pelo nome; o pacote
acrescenta o código IBGE (ver [Município](#município)).

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

# 4. publicar painéis, conciliação e auditorias em resultados/ (versionado)
eletromobilidade publicar

# extrair a tabela PBE Veicular do Inmetro de um PDF de ciclo (só quando sai ciclo novo)
eletromobilidade pbev tabela-pbev-2026.pdf --ciclo 2026

# atualizar a lista de municípios do IBGE (só quando o IBGE cria ou renomeia município)
eletromobilidade municipios

# atualizar as estimativas de população (uma vez por ano, quando o IBGE publica, em agosto)
eletromobilidade populacao
```

`data/raw` e `data/processed` não vão para o repositório; a pasta
[`resultados/`](resultados/LEIAME.md) vai, com o LEIAME descrevendo cobertura e
arquivos. Painéis nacionais e por UF, conciliação e qualidade em CSV; tabelas
por município e de detalhe em Parquet.

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
from eletromobilidade.municipios import dimensao_municipio

longo = pipeline.processar_arquivos(pipeline.localizar_arquivos("data/raw", "combustivel"))
tabelas = pipeline.construir_base_combustivel(longo)
tabelas |= processar_arquivos_modelo(pipeline.localizar_arquivos("data/raw", "marca_modelo"))
tabelas |= conciliar_bases(tabelas)
tabelas["municipios_dimensao"] = dimensao_municipio([tabelas["combustivel_municipio"],
                                                     tabelas["modelo_municipio"]])
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
| `modelo_tipo_{uf,brasil}` | mês × recorte × tipo de veículo | Eletrificados e híbridos leves por tipo (leve, moto, ônibus, caminhão), com a parte de cada tipo |
| `modelos_classificados` | mês × modelo | Auditoria: classe, regra aplicada, total, `revisar`, marca |
| `modelos_dimensao` | modelo | Dimensão do painel: grafia do RENAVAM, marca canônica, origem |
| `conciliacao_{municipio,uf,brasil}` | mês × recorte | Comparação entre as duas bases |
| `qualidade_{combustivel,modelo}` | arquivo mensal | Linhas, frota total, ajustes aplicados e se o mês entrou na série |
| `municipios_dimensao` | município (código IBGE) | Nome oficial, UF, região e as grafias com que a SENATRAN publicou o município |

Os painéis trazem `frota_<classe>` para cada classe, `frota_total`,
`frota_eletrificada` e `participacao_eletrificada = frota_eletrificada / frota_total`.
O painel do Brasil inclui registros sem UF válida; o de UF, não. Nos
eletrificados, esses registros têm perfil de estoque ainda não emplacado (ver
[`docs/ROTEIRO.md`](docs/ROTEIRO.md), item 8): para comparar com vendas, use os
painéis de UF. Toda tabela no
grão de município traz `cod_municipio_ibge`. Os painéis da base por combustível
trazem também `populacao`, `ano_populacao` e `eletrificada_por_mil_habitantes`
(ver [População](#população)).

## Série histórica e qualidade dos arquivos

A série começa em **janeiro/2020** (`processar --desde`, padrão `2020-01`;
`--desde ''` usa todos os arquivos baixados). Como o portal não publicou o
arquivo por combustível de janeiro a maio/2020, a base por combustível começa
de fato em junho/2020.

Disponibilidade verificada em outubro/2026: o arquivo por combustível existe
em 2013 (6 meses), 2014, 2016 (6 meses), 2017, 2018 e de janeiro/2019 em
diante (faltam janeiro a maio/2020); o de marca/modelo, de 2019 em diante no
CKAN (e alguns meses de 2013, 2014 e 2018, parte em `.rar`).

Colunas, tipos e fontes de cada tabela publicada: [`resultados/DICIONARIO.md`](resultados/DICIONARIO.md).

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

## Município

A SENATRAN identifica o município só pelo nome, em caixa alta e sem acento. O
pacote acrescenta o código IBGE de 7 dígitos (`cod_municipio_ibge`), que é o que
liga a base à população, à malha municipal e a qualquer outra tabela do IBGE.

**O nome não serve de identidade, porque muda no meio da série.** Seis municípios
trocam de grafia num mês e seguem com a nova: `EMBU` vira `EMBU DAS ARTES` em
abr/2022, `GOUVEA` vira `GOUVEIA` em mar/2024, `POXOREO` vira `POXOREU` em
mar/2022, e há mais três. Pelo nome, cada grafia seria um município, com a série
cortada ao meio — os 153.787 veículos de Embu das Artes apareciam como um
município que some em mar/2022 e outro que nasce em abr/2022. Pelo código, os seis
têm os 75 meses contínuos.

O casamento é determinístico, sem semelhança aproximada:

1. a lista oficial de municípios da [API de localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades),
   guardada como instantâneo em
   [`dados/municipios.csv`](src/eletromobilidade/dados/municipios.csv) (5.571
   municípios; regerar com `eletromobilidade municipios`);
2. casamento por UF e nome sem acento e sem pontuação — hífen e apóstrofo viram
   espaço, então `SAO JOAO D'ALIANCA` casa com "São João d'Aliança". Resolve
   5.537 das 5.581 grafias da base;
3. as 41 que sobram estão em
   [`dados/municipios_grafias.csv`](src/eletromobilidade/dados/municipios_grafias.csv),
   conferidas uma a uma, com o código e a razão.

| Por que a grafia não casa | Grafias | Exemplo (SENATRAN → IBGE) |
|---|---:|---|
| Preposição | 13 | `SAO MIGUEL D'OESTE` → São Miguel do Oeste |
| Ortografia | 13 | `PARATI` → Paraty, `ARES` → Arez |
| Nome anterior que a SENATRAN não atualizou | 5 | `BOA SAUDE` → Januário Cicco; `SANTAREM` (PB) → Joca Claudino |
| Forma curta do nome | 2 | `BOM JESUS` (GO) → Bom Jesus de Goiás |
| Grafia antiga de município renomeado na série | 6 | `EMBU` → Embu das Artes |
| Erro de digitação | 1 | `BARAO D0 MONTE ALTO` (com zero) → Barão do Monte Alto |
| Distrito publicado como município | 1 | `IBITIUVA` → Pitangueiras, com um veículo por sete meses |

Ficam sem código só os três pseudo-municípios sem UF (`SEM INFORMACAO`,
`NAO IDENTIFICADO`, `NAO SE APLICA`). Qualquer outro município sem código é falha:
`processar` lista a grafia e a frota, e o teste sobre `resultados/` não passa até
ela entrar na tabela de grafias. A tabela também é conferida contra o IBGE na
carga — código inexistente, de outra UF, ou grafia que já casa sozinha com o nome
oficial são erro.

O nome oficial, com acento, está em `municipios_dimensao` (`municipio_ibge`), não
nos fatos: o código basta para ligar os dois. Ali, cada município é uma linha, e
`grafias_senatran` guarda todas as grafias com que ele apareceu.

## População

A base por combustível traz a população residente estimada de cada município e,
com ela, `eletrificada_por_mil_habitantes`. A fonte são as Estimativas de
População do IBGE, [tabela 6579 do SIDRA](https://sidra.ibge.gov.br/tabela/6579),
com a população em 1º de julho de cada ano. A junção é pelo código IBGE, sem
casamento de nome. O instantâneo está em
[`dados/populacao.csv`](src/eletromobilidade/dados/populacao.csv); regerar com
`eletromobilidade populacao` quando o IBGE publicar a estimativa do ano, no fim
de agosto.

**Nem todo ano tem estimativa.** De 2020 em diante há 2020, 2021, 2024, 2025 e
2026: 2022 é o ano do Censo, e 2023 ficou sem estimativa. Cada mês usa a
estimativa do próprio ano; sem ela, a mais próxima **do mesmo lado do Censo
2022**, e por isso 2022 e 2023 usam a de 2024. A coluna `ano_populacao` registra
qual entrou.

**Por que não repetir a de 2021 em 2022 e 2023.** Até 2021 as estimativas
projetam o Censo 2010; a de 2024 já parte do Censo 2022. No Brasil a diferença
entre as duas é de -0,3%, mas no município é outra história:

| Entre as estimativas de | Mediana da variação | Municípios acima de 10% | Acima de 20% |
|---|---:|---:|---:|
| 2020 e 2021 | +0,38% | 6 | 1 |
| 2021 e 2024 | -0,85% | 1.709 | 525 |
| 2024 e 2025 | +0,09% | 3 | 0 |
| 2025 e 2026 | +0,06% | 1 | 0 |

De 2021 para 2024 não é crescimento, é revisão. Para 2022 e 2023, a estimativa de
2024 está sobre o Censo que mediu aqueles anos; a de 2021 estenderia uma
projeção que o Censo corrigiu.

**A consequência é uma quebra em 2022**, e ela é do dado, não do tratamento: a
taxa por habitante de um município comparada entre 2021 e 2022 mede a revisão da
população junto com a frota. Dentro de cada base — jun/2020 a dez/2021, e de
2022 em diante — a comparação vale. A quebra cai ao lado do furo de jan/2022, que
a série já tem.

Três detalhes de construção:

- UF e Brasil recebem a **soma dos municípios do painel**, não o total publicado
  pelo IBGE, para que o Power BI, que sobe do município, reproduza os dois sem
  diferença. No Brasil o numerador inclui a frota sem UF (cerca de 2%), que não
  tem população.
- Nos sete meses em que o distrito de Ibitiúva aparece ao lado da sede, a
  população de Pitangueiras vai só para a linha de Pitangueiras, para não ser
  somada duas vezes.
- Boa Esperança do Norte (MT), instalado em 2025, tem estimativa de 5.877
  habitantes naquele ano, mas na SENATRAN aparece em jul/2025 com 6 veículos e
  chega a 686 em set/2026, sem que Sorriso ou Nova Ubiratã percam frota: o
  registro dele começa do zero, não é transferido. A taxa por habitante do
  município é baixa por construção, e boa parte dos veículos de quem mora lá
  provavelmente segue registrada no município anterior.

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
`TOYOTA/YCROSS XRE-HYBRID` (híbrido convencional, não plug-in), `I/BMW 320I EV11`
e `330I EV51` (código de motor, não elétrico), `I/BMW 325 IX` (o 325ix, não o iX)
e os BYD F0, G3 e F6, carros a combustão anteriores à linha elétrica da marca.

A coluna `revisar` marca modelos de marcas com linha (quase) toda eletrificada
(BYD, GWM, GAC, Omoda/Jaecoo, Zeekr…) que não casaram com nenhuma regra. A CLI
lista esses casos ao final.

## Marca

Do mesmo texto sai a marca, em duas colunas. `marca_renavam` é a grafia como o
RENAVAM publica; `marca` é a forma canônica, que une as grafias da mesma empresa
por [`src/eletromobilidade/dados/marcas.csv`](src/eletromobilidade/dados/marcas.csv).

Extrair a marca não é pegar a primeira palavra: o primeiro elemento do texto pode
ser marcador de importação (`I/`, `IMP/`), a montadora que montou o veículo no
Brasil (`JTA/SUZUKI EN125 YES`) ou o tipo do veículo, em reboque e máquina
(`SR/RANDON SR CA`, `M.A./MASSEY-FERGUSON`). Removido o prefixo, vale tudo o que
vem antes da barra — `HARLEY DAVIDSON/XL883N` é "HARLEY DAVIDSON", não "HARLEY".

A tabela de equivalência cobre as grafias conferidas à mão, que são as de frota
relevante: `GM`, `CHEVROLET` e `CHEV` viram `CHEVROLET` (16,5 milhões de
veículos); `M.BENZ`, `MBENZ`, `MERCEDES` e mais duas viram `MERCEDES-BENZ`.
Grafia fora da tabela segue como está — não há invenção. O que falta sai como
fila ordenada no log de `processar`: as grafias que parecem variante de outra
(`RANDONSP` ao lado de `RANDON`), por frota decrescente.

`marca` é marca comercial, não grupo econômico: Chevrolet e GMC seguem separadas,
como Volvo e Geely. Somar por fabricante pede outra tabela — ver
[`docs/ROTEIRO.md`](docs/ROTEIRO.md).

## Auditoria contra o Inmetro (PBE Veicular)

A classificação por nome é conferida contra a tabela do Programa Brasileiro de
Etiquetagem Veicular, que traz a propulsão **declarada pelo fabricante** e a
categoria de porte, versão por versão. É a única fonte pública brasileira que
separa PHEV de HEV por versão — nem o campo combustível do RENAVAM separa.

A fonte é PDF, sem CSV equivalente no dados.gov.br, e com o texto desenhado
caractere a caractere: as colunas saem pelas bordas da tabela, não pelo fluxo do
texto. Por isso a extração não roda no `processar`. Ela gera um instantâneo
versionado, e é esse arquivo que o pacote lê:

```bash
# baixe o PDF do ciclo em gov.br/inmetro e extraia uma vez
eletromobilidade pbev tabela-pbev-2026.pdf --ciclo 2026
```

O ciclo 2026 rendeu 972 versões, 49 marcas e 309 modelos. O PDF declara 976
modelos/versões no próprio cabeçalho, com 114 híbridos e 112 plug-in; a extração
fecha em 114 e 111 — a conferência está nesse número.

Três colunas entram em `modelos_classificados`:

| Coluna | O que é |
|---|---|
| `pbe_classes` | classes que a linha do modelo tem no PBE, separadas por `\|`. Vazio quando o modelo não casou (moto, ônibus, caminhão, modelo fora de linha) |
| `pbe_categoria` | porte do PBE (Médio, Picape, Utilitário Esportivo Compacto…) |
| `pbe_aviso` | a divergência, com a direção |

A junção nunca reduz o modelo a uma propulsão só. Corolla tem versão a combustão
e versão híbrida na mesma linha do PBE, e o aviso olha o **conjunto**: por isso
`TOYOTA/COROLLA GLI` e `TOYOTA/COROLLA ALTIS HV` convivem sem acusação falsa.

As duas direções do aviso se leem de formas opostas:

- **`sem_versao_no_pbe`** — a regra atribuiu classe eletrificada que o PBE não
  registra para o modelo. Falso positivo provável, e a fila mais acionável: 20
  modelos e 6.935 veículos em set/2026. Foi assim que apareceu
  `I/BMW 320I EV11`, classificado elétrico pela regra genérica `\bEV\d*\b` —
  "EV11" é código de motor da BMW, não marcador elétrico. Corrigido em
  21/10/2026, com os outros BMW de código EV (ver Classificação por modelo).
- **`pbe_so_eletrificado`** — a regra disse combustão e toda versão do modelo no
  PBE é eletrificada. 505 modelos e 418 mil veículos, mas **a maioria é geração
  antiga, não regra faltando**: o PBE do ciclo só traz o que está em linha, e
  `I/MMC OUTLANDER 2.0` é o Outlander a combustão de antes do PHEV, como
  `I/HONDA CR-V LX` é a geração anterior ao CR-V só híbrido. Confira o ano de
  fabricação antes de criar regra.

`hibrido_leve` nunca gera aviso, e isso é informação: o PBE não tem essa
categoria e registra `FIAT/PULSE AUDACE HYB` e `JEEP/RENEGADE LONGIT HYB` como
**combustão**. É respaldo externo, com fonte citável, para a decisão deste
projeto de manter híbrido leve fora da frota eletrificada.

**Cobertura, que é parcial por construção.** O PBE é só de veículo leve novo
ensaiado no ciclo: 79,1% da frota eletrificada da base por modelo casa com uma
linha e ganha porte. O que fica fora não é, como se supunha, quase tudo moto e
ônibus: dois terços ainda são carro que não casou, por geração antiga ou nome
abreviado (`TOYOTA/CCROSS XRX HYBRID`, o Corolla Cross, com 69 mil veículos). Ver
[Tipo de veículo](#tipo-de-veículo).

## Tipo de veículo

"Frota eletrificada" soma automóvel, scooter, ônibus e caminhão num número só, e
a SENATRAN não publica tabela que cruze tipo com combustível: o arquivo por
combustível (`D_`) não tem tipo, e o por tipo (`G_`) não tem combustível. O tipo
sai, então, do modelo, na base por modelo, para os eletrificados e híbridos leves
do detalhe (`tipo` em `modelo_eletrificados`, `modelos_classificados` e
`modelos_dimensao`, e os painéis `modelo_tipo_{uf,brasil}`).

Cinco grupos, que agregam os tipos do RENAVAM:

| Grupo | Tipos do RENAVAM |
|---|---|
| `leve` | automóvel, camioneta, caminhonete, utilitário (inclui SUV, picape e van) |
| `moto` | motocicleta, motoneta, ciclomotor, triciclo, side-car |
| `onibus` | ônibus, micro-ônibus |
| `caminhao` | caminhão, caminhão-trator, chassi-plataforma |
| `outros` | quadriciclo, trator, bonde, reboque, semirreboque, outros |

**Ao contrário da tecnologia, o tipo de um modelo com nome não é ambíguo.**
"HYBRID" pode ser plug-in ou não; um BYD D9W é ônibus e um Voltz EV1 é scooter.
Duas fontes, nesta ordem:

1. regra de [`dados/tipos.csv`](src/eletromobilidade/dados/tipos.csv) que dê tipo
   não leve: carrocerias de ônibus no nome (Caio/Induscar, Marcopolo, Comil),
   chassis BYD D9/D11/K, caminhões VW e-Delivery, BYD eT, JAC e-JT e iEV1200T,
   Volvo FM; marcas só de duas e três rodas (GCX, Vmoto, Aima, Voltz, Yadea…) e a
   potência em W ou kW no nome (`3.000W`, `3KW`), que é como o RENAVAM grafa
   scooter e ciclomotor elétrico;
2. o **PBE Veicular**, que só tem veículo leve: modelo que casou com ele é
   `leve`, com `origem_tipo = 'pbe'`. É a fonte de 78,7% da frota eletrificada;
3. regra de leve, para o carro que não casou com o PBE. Marca que só vende
   veículo leve entra inteira; marca que também faz moto, ônibus ou caminhão
   (Honda, BMW, Volvo, Mercedes-Benz, VW, BYD, JAC) entra só pelas famílias de
   carro, para que um ônibus novo da BYD não vire carro em silêncio.

As 27 regras foram conferidas contra os modelos eletrificados das duas datas,
hoje 921. Dois ficaram sem tipo, com 3 veículos, porque nenhuma fonte identifica o
nome (`I/BYD TB3` e `I/GUANGZHOU Z1 ELETRIC`). Um caso foi decidido **por exclusão, não por fonte**, e a nota da regra diz
isso: `FLASH/MV ING ELETRIC`, 392 elétricos de fabricação 2012, poucos por
município no Norte e no Centro-Oeste. Em 2012 o país tinha poucas dezenas de
carros elétricos, então só cabe scooter ou ciclomotor.

**Os controles.**

- Regra que dá tipo não leve a modelo que está no PBE é divergência
  (`tipo_aviso = 'pbe_diverge'`), e o teste sobre `resultados/` não passa com
  nenhuma. Foi assim que a BYD eT3, que uma regra genérica de caminhão pegava,
  voltou a ser o que o Inmetro registra: van.
- Modelo sem regra nem PBE fica sem tipo: `processar` lista, e o teste falha se
  isso passar de 0,1% da frota do detalhe no mês.
- Conferência pontual contra a tabela oficial Frota por Município e Tipo de
  set/2026: em nenhum dos municípios os eletrificados de um grupo passam o total
  daquele grupo. É limite fraco, porque a frota eletrificada é uma fração pequena
  de cada tipo, mas pega erro grosso. Não é teste automático: a tabela não é
  versionada.

**O `G_` não serve de total de controle**, como o roteiro previa. Ele não tem
combustível; só controlaria uma classificação de tipo da frota inteira, os 40 mil
modelos, e não a da frota eletrificada.

**Resultado.** Base por modelo, parte de cada tipo na frota eletrificada:

| | dez/2020 | set/2026 |
|---|---:|---:|
| Leve | 90,7% | 92,8% |
| Moto | 8,9% | 6,9% |
| Caminhão | 0,2% | 0,2% |
| Ônibus | 0,2% | 0,1% |
| **Moto entre os elétricos a bateria** | **66,8%** | **16,9%** |

Plug-in e híbrido convencional são 100% leves. O número que muda a leitura é o
último: em 2020, dois terços dos elétricos a bateria eram scooter ou moto;
hoje é um sexto. O de 2020 vale com ressalva: naquele mês a base por modelo
só reconhece pelo nome 61% dos elétricos que o campo combustível registra nas
UFs válidas, e o que ela não reconhece pode ter outra composição. Os híbridos da Yamaha (Ray ZR e Fluo, 17 mil) são híbridos leves e ficam
fora da frota eletrificada, como os carros híbridos leves.

**Leia como composição.** A base por modelo acha 18% menos eletrificados que a
base por combustível, e a contagem absoluta por tipo herda essa diferença. Por
isso os painéis trazem `participacao_tipo`, e é ela que se cita.

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
| Elétrico | 395.132 | 377.482 | 0,955 |
| Híbrido plug-in | 79.245 | 352.706 | 4,45 |
| Híbrido convencional | 709.697 | 260.628 | 0,37 |
| Híbridos, soma | 788.942 | 613.334 | 0,78 |
| Híbridos + híbridos leves do modelo | 788.942 | 730.941 | 0,93 |

Leitura:

- A frota total coincide em todas as UFs: os dois arquivos cobrem o mesmo
  universo.
- Elétricos: a base por modelo recupera 95,5% nas UFs válidas (de 92,5% a
  99,5% por UF) e 91,4% no Brasil. O resíduo maior está no grupo de
  UF/município "Sem Informação" (3,1 milhões de veículos, quase todos sem ano
  de fabricação). Nos eletrificados, o grupo tem perfil de estoque cadastrado e
  ainda não emplacado: são os lançamentos mais recentes, e ele cai depois que o
  estoque é vendido.
- **O campo combustível não separa plug-in de híbrido convencional.** A base
  por modelo tem 4,5 vezes mais plug-ins que o rótulo HIBRIDO PLUG-IN: a maior
  parte dos PHEV está registrada como GASOLINA/ELETRICO ou similar. Para a
  separação PHEV × HEV, usar a base por modelo.
- **O campo combustível conta híbridos leves como híbridos.** Somando os
  híbridos leves da base por modelo, os híbridos fecham em 93%. Como a decisão
  do projeto é excluir híbridos leves, a base por combustível superestima a
  frota híbrida.

Teste das regras num mês antigo (dezembro/2019, mesmas regras calibradas em
2026): frota total idêntica; elétricos 4.462 pelo modelo contra 4.367 pelo
combustível (102%); híbridos (plug-in + convencional) em 96,6%. Esse teste é
anterior à correção dos BMW com código de motor EV (21/10/2026), e os 102%
provavelmente incluem esses falsos elétricos: em dez/2020, a mesma correção
derrubou o reconhecimento de elétricos nas UFs válidas de 99% para 61%. Em 2019 o rótulo
HIBRIDO PLUG-IN ainda não existia: os 2.442 plug-ins identificados pelo nome
(Volvo T8, BMW 330e etc.) estão, no campo combustível, entre os híbridos.

Classificações confirmadas por conhecimento de mercado (não pelo texto):
Shineray PT2/PT3/PT4/PT7 e SE1/SE2/SE3 são elétricos; GAC GS4 é híbrido
convencional a gasolina.

## Limitações conhecidas

1. **Tipo de veículo.** O arquivo por combustível não traz o tipo (automóvel,
   motocicleta, ônibus, caminhão). A `participacao_eletrificada` é, portanto,
   sobre a frota total registrada, não sobre veículos leves. O tipo existe só na
   base por modelo, e se lê como composição (ver [Tipo de veículo](#tipo-de-veículo)).
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
   que já não circulam e não foram baixados. Na prática a baixa quase não
   aparece: os eletrificados leves fabricados até 2018 eram 12.298 em dez/2020
   e 12.317 em set/2026.
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

## O painel

A camada de apresentação está em [`pbi/`](pbi/MODELO.md), especificada em
arquivos de texto em vez de um `.pbix` versionado — binário em Git não rende
revisão nem diff. O `.pbix` se monta a partir deles em cerca de vinte minutos,
pelo passo a passo de [`pbi/MODELO.md`](pbi/MODELO.md#como-montar-o-pbix).

| Arquivo | O que é |
|---|---|
| [`pbi/MODELO.md`](pbi/MODELO.md) | Modelo estrela: tabelas, grão, relacionamentos, decisões, ressalvas e tabela de validação |
| [`pbi/PAGINAS.md`](pbi/PAGINAS.md) | As cinco páginas do relatório, com a forma de cada visual e o porquê |
| [`pbi/REFRESH.md`](pbi/REFRESH.md) | Ciclo de atualização mensal e publicação no Service |
| [`pbi/powerquery/`](pbi/powerquery) | Onze consultas M: o parâmetro da pasta, uma por tabela do modelo e a função que monta a chave de município |
| [`pbi/dax/`](pbi/dax) | `dCalendario` e as medidas |
| [`pbi/tema.json`](pbi/tema.json) | Tema do Power BI, com paleta categórica verificada para daltonismo |

Duas coisas que o painel precisa deixar claro, e que estão documentadas nos dois
arquivos: **frota é estoque registrado, não emplacamento** — somar meses não dá
o ano, e a variação mensal é saldo, não venda; e **a divisão entre plug-in e
híbrido convencional não vale pelo campo combustível**, que registra com o
rótulo próprio só um quarto dos plug-ins vendidos. O painel ainda tira a
tecnologia dessa base; a troca é pendência do roteiro.

## Próximos passos

Em [`docs/ROTEIRO.md`](docs/ROTEIRO.md), em ordem de valor. O código IBGE de
município, a população por município e o tipo de veículo estão feitos, e a base
foi comparada com as vendas da ABVE (item 8). Os próximos são as pendências dessa
comparação: as regras de plug-in que faltam e a fonte da divisão por tecnologia
no painel. Depois, ampliar a série da base por modelo e o furo de jan/2022.
