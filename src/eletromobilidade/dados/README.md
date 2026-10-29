# Regras e tabelas de referência

Tudo o que decide uma classificação ou liga a base a outra fonte está aqui, em
CSV versionado, e não no código. Mudar um destes arquivos muda os resultados:
rode `processar` e `publicar` de novo.

| Arquivo | O que é | Seção |
|---|---|---|
| `combustiveis.csv` | Rótulo de combustível do RENAVAM → classe | [Combustível](#combustível) |
| `modelos.csv` | Regras ordenadas: texto "Marca Modelo" → classe | [Modelo](#modelo) |
| `marcas.csv` | Grafias de marca → marca canônica | [Marca](#marca) |
| `tipos.csv` | Regras de tipo de veículo | [Tipo de veículo](#tipo-de-veículo) |
| `pbev.csv` | Instantâneo da tabela PBE Veicular do Inmetro | [PBE Veicular](#pbe-veicular-inmetro) |
| `municipios.csv`, `municipios_grafias.csv` | Municípios do IBGE e as grafias da SENATRAN que não casam sozinhas | [Município](#município) |
| `populacao.csv` | Estimativas de população do IBGE | [População](#população) |

Os CSVs de regra usam `;` como separador e têm uma coluna `nota`, que não pode
conter `;`. A carga falha com a linha indicada quando isso acontece.

## Combustível

`combustiveis.csv` liga cada rótulo do RENAVAM a uma classe; pode ser
substituído por `processar --tabela-combustiveis`. Rótulos fora da tabela são
classificados por regra textual e aparecem com `origem_classificacao = "regra"`
na auditoria; a CLI avisa quais são.

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

Os códigos 06 (ELETRICO/FONTE INTERNA) e 07 (ELETRICO/FONTE EXTERNA) vêm de uma
tabela antiga do RENAVAM, sem significado operacional documentado de forma
inequívoca; os dois contam como `eletrico`.

**Plug-in vs. híbrido convencional.** `hibrido_plug_in` (PHEV) recarrega na
tomada; `hibrido` (HEV) só pelo motor a combustão e pela frenagem. No campo
combustível só o rótulo HIBRIDO PLUG-IN identifica PHEV, e ele pega 22% dos
plug-ins vendidos: o resto está em GASOLINA/ELETRICO e similares, junto com
híbridos leves flex (Fiat "Hybrid" 12 V). O rótulo só existe desde abr/2022, e o
de célula de combustível desde nov/2022.

## Modelo

O texto "Marca Modelo" (ex.: `I/BYD DOLPHIN GS 180EV`, `I/GWM HAVAL H6 PHEV19`,
`TOYOTA/COROLLA ALTIS HV`) é classificado pelas regras de `modelos.csv`
(`classe;padrao;nota`; substituível por `processar --regras-modelos`). **A
primeira regra cujo padrão casa define a classe** (regex sobre o texto sem
acento, em caixa alta); sem regra, `combustao`. O número da regra aplicada fica
em `modelos_classificados`.

| Classe | Exemplos reais | Entra em `frota_eletrificada` |
|---|---|---|
| `eletrico` | BYD Dolphin, Tesla, Volvo EX30, Renault E-Kwid, Peugeot E-Expert | sim |
| `hibrido_plug_in` | BYD Song/King DM, Haval H6 PHEV/GT, Volvo T8, BMW 330e, Jeep 4xe, Outlander PHEV | sim |
| `hibrido` | Corolla/Corolla Cross Hybrid, Lexus ES300h, Haval H6 HEV | sim |
| `celula_combustivel` | Mirai (se aparecer) | sim |
| `hibrido_leve` | Fiat Pulse/Fastback Hybrid (12 V), Kia Sportage MHEV, Caoa Chery "H"/"HA" | **não** (coluna própria) |
| `combustao` | demais | não |
| `nao_motorizado` | reboques (`R/`) e semirreboques (`SR/`) | não |

**As regras por marca vêm antes das genéricas** porque os nomes têm armadilhas,
cobertas por testes em `tests/test_modelos.py`:

- `VW/8.150E DELIVERY` (diesel, "E" de eletrônico) e `VW/POLO 1.6 E-FLEX` (flex);
- `HYUNDAI/HB20 EVOLUTION` e `CHEV/…`, que contêm "EV"/"HEV";
- `TOYOTA/YCROSS XRE-HYBRID`, híbrido convencional, não plug-in;
- `I/BMW 320I EV11` e `330I EV51` (código de motor) e `I/BMW 325 IX` (o 325ix,
  não o iX);
- os BYD F0, G3 e F6, carros a combustão anteriores à linha elétrica da marca;
- os plug-ins de nome abreviado: Outlander `SIGNTR E`, Mercedes-AMG `EP`,
  Panamera `4EHST`/`TSEHS`, Volvo `INSC EXPRES`.

Algumas classes vêm de conhecimento de mercado e não do texto, e a nota da regra
diz isso: Stellantis e Caoa Chery "Hybrid" como híbrido leve, Audi "HIBRIDO" como
híbrido (pode ser 48 V), Jaecoo 7 como plug-in, BYD sem "DM" como elétrico,
Shineray PT/SE como elétricos, GAC GS4 como híbrido, Volvo XC60/XC90
Inscription Express como plug-in.

A coluna `revisar` marca modelos de marcas com linha (quase) toda eletrificada
(BYD, GWM, GAC, Omoda/Jaecoo, Zeekr…) que não casaram com nenhuma regra; a CLI
lista esses casos ao final de `processar`.

## Marca

Do mesmo texto sai a marca, em duas colunas: `marca_renavam`, a grafia como o
RENAVAM publica, e `marca`, a forma canônica dada por `marcas.csv`.

Extrair a marca não é pegar a primeira palavra: o primeiro elemento pode ser
marcador de importação (`I/`, `IMP/`), a montadora que montou o veículo no Brasil
(`JTA/SUZUKI EN125 YES`) ou o tipo do veículo (`SR/RANDON SR CA`,
`M.A./MASSEY-FERGUSON`). Removido o prefixo, vale tudo o que vem antes da barra:
`HARLEY DAVIDSON/XL883N` é "HARLEY DAVIDSON".

A tabela cobre as grafias conferidas à mão, as de frota relevante: `GM`,
`CHEVROLET` e `CHEV` viram `CHEVROLET` (16,5 milhões de veículos); `M.BENZ`,
`MBENZ`, `MERCEDES` e mais duas viram `MERCEDES-BENZ`. Grafia fora da tabela
segue como está. O que falta sai como fila no log de `processar`: as grafias que
parecem variante de outra (`RANDONSP` ao lado de `RANDON`), por frota
decrescente.

`marca` é marca comercial, não grupo econômico: Chevrolet e GMC seguem
separadas, como Volvo e Geely.

## Tipo de veículo

A SENATRAN não publica tabela que cruze tipo com combustível: o arquivo `D_` não
tem tipo, e o `G_` não tem combustível. O tipo sai do modelo, na base por modelo,
para os eletrificados e híbridos leves (`tipo` em `modelo_eletrificados`,
`modelos_classificados` e `modelos_dimensao`, e os painéis `modelo_tipo_*`).

| Grupo | Tipos do RENAVAM |
|---|---|
| `leve` | automóvel, camioneta, caminhonete, utilitário (inclui SUV, picape e van) |
| `moto` | motocicleta, motoneta, ciclomotor, triciclo, side-car |
| `onibus` | ônibus, micro-ônibus |
| `caminhao` | caminhão, caminhão-trator, chassi-plataforma |
| `outros` | quadriciclo, trator, bonde, reboque, semirreboque, outros |

Ao contrário da tecnologia, o tipo de um modelo com nome não é ambíguo: um BYD
D9W é ônibus e um Voltz EV1 é scooter. Três fontes, nesta ordem:

1. regra de `tipos.csv` que dê tipo não leve: carroceria de ônibus no nome
   (Caio/Induscar, Marcopolo, Comil), chassis BYD D9/D11/K, caminhões VW
   e-Delivery, BYD eT, JAC e-JT e iEV1200T, Volvo FM; marcas só de duas e três
   rodas (GCX, Vmoto, Aima, Voltz, Yadea…) e a potência em W ou kW no nome
   (`3.000W`, `3KW`), que é como o RENAVAM grafa scooter elétrica;
2. o **PBE Veicular**, que só tem veículo leve: modelo que casou com ele é
   `leve`, com `origem_tipo = 'pbe'`. É a fonte de 78,7% da frota eletrificada;
3. regra de leve, para o carro que não casou com o PBE. Marca que só vende
   veículo leve entra inteira; marca que também faz moto, ônibus ou caminhão
   (Honda, BMW, Volvo, Mercedes-Benz, VW, BYD, JAC) entra só pelas famílias de
   carro, para que um ônibus novo da BYD não vire carro em silêncio.

Dois modelos ficam sem tipo, com 3 veículos, porque nenhuma fonte identifica o
nome (`I/BYD TB3` e `I/GUANGZHOU Z1 ELETRIC`). Um caso foi decidido por
exclusão, e a nota diz isso: `FLASH/MV ING ELETRIC`, 392 elétricos de fabricação
2012, que só podem ser scooter ou ciclomotor (em 2012 o país tinha poucas dezenas
de carros elétricos).

Os controles:

- regra que dá tipo não leve a modelo que está no PBE é divergência
  (`tipo_aviso = 'pbe_diverge'`), e o teste sobre `resultados/` não passa com
  nenhuma. Foi assim que a BYD eT3 voltou a ser o que o Inmetro registra: van;
- modelo sem regra nem PBE fica sem tipo: `processar` lista, e o teste falha se
  isso passar de 0,1% da frota do detalhe no mês;
- conferência pontual contra a Frota por Município e Tipo de set/2026: em nenhum
  município os eletrificados de um grupo passam o total daquele grupo. É limite
  fraco, e não é teste automático, porque a tabela não é versionada.

O `G_` não serve de total de controle: sem combustível, só controlaria uma
classificação de tipo da frota inteira, e não a da frota eletrificada.

## PBE Veicular (Inmetro)

A tabela do Programa Brasileiro de Etiquetagem Veicular traz a propulsão
**declarada pelo fabricante** e a categoria de porte, versão por versão. É a
única fonte pública brasileira que separa PHEV de HEV por versão.

A fonte é PDF, sem CSV equivalente, com o texto desenhado caractere a caractere:
as colunas saem pelas bordas da tabela, não pelo fluxo do texto. Por isso a
extração não roda em `processar`; ela gera `pbev.csv` uma vez por ciclo:

```bash
eletromobilidade pbev tabela-pbev-2026.pdf --ciclo 2026
```

O ciclo 2026 rendeu 972 versões, 49 marcas e 309 modelos. O PDF declara 114
híbridos e 112 plug-in no cabeçalho; a extração fecha em 114 e 111.

Três colunas entram em `modelos_classificados`: `pbe_classes` (classes que a
linha do modelo tem no PBE, separadas por `|`), `pbe_categoria` (porte) e
`pbe_aviso` (a divergência). A junção nunca reduz o modelo a uma propulsão só:
Corolla tem versão a combustão e híbrida na mesma linha, e o aviso olha o
conjunto, então `TOYOTA/COROLLA GLI` e `TOYOTA/COROLLA ALTIS HV` convivem sem
acusação falsa.

As duas direções do aviso se leem de formas opostas (números de set/2026):

- **`sem_versao_no_pbe`**: a regra deu classe eletrificada que o PBE não
  registra para o modelo. Falso positivo provável e a fila mais acionável: 19
  modelos e 6.879 veículos. Foi assim que apareceu `I/BMW 320I EV11`.
- **`pbe_so_eletrificado`**: a regra disse combustão e toda versão do modelo no
  PBE é eletrificada. 489 modelos e 414 mil veículos, mas a maioria é geração
  antiga: `I/MMC OUTLANDER 2.0` é o Outlander a combustão de antes do PHEV.
  Confira o ano de fabricação antes de criar regra.

`hibrido_leve` nunca gera aviso, e isso é informação: o PBE registra
`FIAT/PULSE AUDACE HYB` como combustão, o que respalda manter o híbrido leve fora
da frota eletrificada.

A cobertura é parcial por construção: o PBE é só de veículo leve novo ensaiado
no ciclo, e 79,1% da frota eletrificada da base por modelo casa com uma linha. O
que fica fora é, em dois terços, carro de geração antiga ou nome abreviado
(`TOYOTA/CCROSS XRX HYBRID`, o Corolla Cross, com 69 mil veículos).

## Município

A SENATRAN identifica o município só pelo nome, em caixa alta e sem acento. O
pacote acrescenta o código IBGE de 7 dígitos (`cod_municipio_ibge`), que liga a
base à população, à malha e a qualquer outra tabela do IBGE.

**O nome não serve de identidade, porque muda no meio da série.** Seis
municípios trocam de grafia num mês e seguem com a nova: `EMBU` vira `EMBU DAS
ARTES` em abr/2022, `GOUVEA` vira `GOUVEIA` em mar/2024, `POXOREO` vira `POXOREU`
em mar/2022, e há mais três. Pelo nome, os 153.787 veículos de Embu das Artes
apareciam como um município que some em mar/2022 e outro que nasce em abr/2022;
pelo código, os seis têm os 75 meses contínuos.

O casamento é determinístico, sem semelhança aproximada:

1. a lista oficial do IBGE em `municipios.csv` (5.571 municípios; regerar com
   `eletromobilidade municipios`);
2. casamento por UF e nome sem acento e sem pontuação (hífen e apóstrofo viram
   espaço, então `SAO JOAO D'ALIANCA` casa com "São João d'Aliança"). Resolve
   5.537 das 5.581 grafias;
3. as 41 que sobram estão em `municipios_grafias.csv`, conferidas uma a uma,
   com o código e a razão.

| Por que a grafia não casa | Grafias | Exemplo (SENATRAN → IBGE) |
|---|---:|---|
| Preposição | 13 | `SAO MIGUEL D'OESTE` → São Miguel do Oeste |
| Ortografia | 13 | `PARATI` → Paraty, `ARES` → Arez |
| Nome anterior que a SENATRAN não atualizou | 5 | `BOA SAUDE` → Januário Cicco |
| Forma curta do nome | 2 | `BOM JESUS` (GO) → Bom Jesus de Goiás |
| Grafia antiga de município renomeado na série | 6 | `EMBU` → Embu das Artes |
| Erro de digitação | 1 | `BARAO D0 MONTE ALTO` (com zero) → Barão do Monte Alto |
| Distrito publicado como município | 1 | `IBITIUVA` → Pitangueiras |

Ficam sem código só os três pseudo-municípios sem UF (`SEM INFORMACAO`, `NAO
IDENTIFICADO`, `NAO SE APLICA`). Qualquer outro município sem código é falha:
`processar` lista a grafia e a frota, e o teste sobre `resultados/` não passa até
ela entrar na tabela de grafias. A tabela também é conferida contra o IBGE na
carga: código inexistente, de outra UF, ou grafia que já casa sozinha são erro.

O nome oficial, com acento, está em `municipios_dimensao` (`municipio_ibge`), com
todas as grafias que o município teve na série (`grafias_senatran`).

## População

A base por combustível traz a população residente estimada de cada município e,
com ela, `eletrificada_por_mil_habitantes`. A fonte é a [tabela 6579 do
SIDRA](https://sidra.ibge.gov.br/tabela/6579), população em 1º de julho, unida
pelo código IBGE. Regerar `populacao.csv` com `eletromobilidade populacao` quando
o IBGE publicar a estimativa do ano, no fim de agosto.

**Nem todo ano tem estimativa.** De 2020 em diante há 2020, 2021, 2024, 2025 e
2026: 2022 é o ano do Censo, e 2023 ficou sem estimativa. Cada mês usa a
estimativa do próprio ano; sem ela, a mais próxima **do mesmo lado do Censo
2022**, e por isso 2022 e 2023 usam a de 2024. A coluna `ano_populacao` registra
qual entrou.

Repetir a de 2021 em 2022 e 2023 estenderia uma projeção que o Censo corrigiu.
Até 2021 as estimativas projetam o Censo 2010; a de 2024 já parte do Censo 2022.
No Brasil a diferença é de −0,3%, mas no município não:

| Entre as estimativas de | Mediana da variação | Municípios acima de 10% | Acima de 20% |
|---|---:|---:|---:|
| 2020 e 2021 | +0,38% | 6 | 1 |
| 2021 e 2024 | −0,85% | 1.709 | 525 |
| 2024 e 2025 | +0,09% | 3 | 0 |
| 2025 e 2026 | +0,06% | 1 | 0 |

**A consequência é uma quebra em 2022**, que é do dado: a taxa por habitante de
um município comparada entre 2021 e 2022 mede a revisão da população junto com a
frota. Dentro de cada base, jun/2020 a dez/2021 e de 2022 em diante, a
comparação vale.

Três detalhes de construção:

- UF e Brasil recebem a soma dos municípios do painel, não o total publicado pelo
  IBGE, para que o Power BI, que sobe do município, reproduza os dois sem
  diferença. No Brasil o numerador inclui a frota sem UF (cerca de 2%), que não
  tem população.
- Nos sete meses em que o distrito de Ibitiúva aparece ao lado da sede, a
  população de Pitangueiras vai só para a linha de Pitangueiras.
- Boa Esperança do Norte (MT), instalado em 2025, aparece na SENATRAN em jul/2025
  com 6 veículos e chega a 686 em set/2026, sem que Sorriso ou Nova Ubiratã
  percam frota: o registro começa do zero. A taxa por habitante do município é
  baixa por construção.
