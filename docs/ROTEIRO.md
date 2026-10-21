# Roteiro

Estado em 21/10/2026. O pipeline Python está fechado e testado (271 testes); a
camada do Power BI está especificada em [`pbi/`](../pbi/MODELO.md) e o `.pbix`
ainda precisa ser montado. O que falta está abaixo, em ordem de valor.

As tabelas de `resultados/` estão em dia com o código, regeradas em 21/10 com a
série completa de combustível (76 arquivos) e os dois meses da base por modelo.
Reproduziram a execução de 20/10 com diferença zero em todas as colunas que já
existiam; o que mudou foi a coluna `cod_municipio_ibge`, a dimensão de município,
as três colunas de população nos painéis da base por combustível e o tipo de
veículo na base por modelo. Regerá-las exige os arquivos da SENATRAN em `data/raw`, que não são
versionados: `baixar`, depois `processar` e `publicar`.

## 1. Código IBGE e população por município — feito

**Feito em 21/10/2026.** Toda tabela no grão de município traz
`cod_municipio_ibge`, e `resultados/municipios_dimensao.parquet` tem uma linha
por município, com o nome oficial do IBGE. O casamento é determinístico: 5.537
das 5.581 grafias da base casam pelo nome sem acento e sem pontuação, e as 41
que sobram estão em `src/eletromobilidade/dados/municipios_grafias.csv`,
conferidas uma a uma. Ficam sem código só os três pseudo-municípios sem UF. O
teste que este item pedia existe e roda sobre `resultados/`: falha se sobrar
município com UF e sem código. Detalhe no README, seção Município.

**O resíduo não era só grafia.** Seis municípios trocam de nome no meio da série
— `EMBU` vira `EMBU DAS ARTES` em abr/2022, `GOUVEA` vira `GOUVEIA` em mar/2024
—, e pelo nome cada um deles era dois municípios, com a série cortada no mês da
troca. A dimensão do painel era por nome e tinha 5.581 membros; passou a ser por
código, com 5.574, e os seis têm os 75 meses contínuos.

**População, também feita em 21/10/2026.** Os painéis da base por combustível
trazem `populacao` e `eletrificada_por_mil_habitantes`, a medida que uma política
de recarga usa e o motivo de este item vir primeiro. A fonte escolhida foram as
estimativas anuais do IBGE (SIDRA 6579), não o Censo 2022, por darem série. A
junção é pelo código, sem casar nome nenhum.

**A ressalva que acompanha a taxa por habitante.** Não há estimativa para 2022 nem
2023, e a base das estimativas muda no meio: até 2021 projetam o Censo 2010, de
2024 em diante partem do Censo 2022. Entre as duas, 1.709 municípios mudam mais de
10%. 2022 e 2023 usam a estimativa de 2024, que está do mesmo lado do Censo, e a
quebra fica em 2022. A taxa de um município comparada através dela mede revisão de
população junto com frota. Detalhe no README, seção População.

**O mapa municipal também está destravado.** A malha do IBGE identifica o
município pelo mesmo código (ver [`pbi/PAGINAS.md`](../pbi/PAGINAS.md)). Ela tem
5.570 polígonos: falta Boa Esperança do Norte, mais novo que a malha.

## 2. Ampliar a série da base por modelo

**Por que.** Hoje são dois meses, dez/2020 e set/2026. Não há série temporal por
marca, modelo ou ano de fabricação — a página 3 do relatório é uma fotografia, e
a conciliação tem só dois pontos. Com doze meses já se vê a entrada dos modelos
chineses no tempo, que é a pergunta mais feita sobre o assunto.

**Custo.** Cada mês são ~22 milhões de linhas, 137 MB compactado, cerca de 1,5
min de processamento, e o cache mensal em `data/interim/` já evita releitura. O
gargalo é download, não CPU.

**Sugestão.** Dezembro de cada ano desde 2020, mais os meses de 2026. Seis a
oito meses dão série anual sem o custo de 75.

## 3. Tipo de veículo — feito

**Feito em 21/10/2026.** Os eletrificados e híbridos leves da base por modelo
têm tipo de veículo — leve, moto, ônibus, caminhão, outros —, publicado em
`modelo_eletrificados`, `modelos_dimensao` e nos painéis `modelo_tipo_{uf,brasil}`.
Detalhe no README, seção Tipo de veículo. A resposta à pergunta que motivou o
item, base por modelo:

| | dez/2020 | set/2026 |
|---|---:|---:|
| Leve, na frota eletrificada | 91,1% | 92,8% |
| Moto, na frota eletrificada | 8,5% | 6,9% |
| **Moto, entre os elétricos a bateria** | **48,6%** | **16,9%** |

Ônibus e caminhão somam menos de 0,5%. Plug-in e híbrido convencional são todos
leves. Leia como composição: a base por modelo acha 18% menos eletrificados que a
por combustível, e a contagem por tipo herda isso.

**Duas premissas deste item estavam erradas, e o trabalho mostrou.**

- *"Os 20,9% fora do PBE concentram moto, scooter e ônibus."* Não: dois terços do
  que fica fora do PBE ainda é carro, que não casou por geração antiga ou nome
  abreviado — o maior é o Corolla Cross, `TOYOTA/CCROSS XRX HYBRID`, com 69 mil.
  O PBE não bastava; a tabela de regras precisou cobrir carro também.
- *"`G_` como total de controle transformaria a inferência em erro medido."* Não
  transforma: `G_` não tem combustível, então só controlaria uma classificação de
  tipo da frota inteira (40 mil modelos), não a da eletrificada. Ficou como
  conferência pontual — em nenhum município os eletrificados de um grupo passam o
  total oficial do grupo em set/2026 —, que pega erro grosso e não mede erro fino.

**O que faz o número ser defensável** é outra coisa: o tipo de um modelo com nome
não é ambíguo, como a tecnologia é. O PBE dá o tipo de 78,7% da frota com fonte
externa; as 27 regras de `dados/tipos.csv` foram conferidas contra os 934 modelos;
regra que contradiz o PBE é divergência e derruba o teste — foi o que pegou a BYD
eT3, van, que uma regra de caminhão levava. Sem tipo ficaram 3 veículos. Um caso
foi decidido por exclusão, e a regra diz isso (`FLASH/MV ING ELETRIC`, ver o
README).

**De passagem, erros da classificação de tecnologia**, que não são deste item e
não foram corrigidos. Em set/2026, na base por modelo:

- BMW com código de motor `EV` no nome, contados como elétricos:
  `I/BMW 320I EV11` (1.242), `330I EV51` (632, com a versão Security),
  `325I EV31` (391), `325I PRO EV39` (58) e `330I EV53` (2). O EV11 é o caso que o
  README cita como achado pela auditoria do PBE — achado, mas a regra não mudou;
- `I/BMW 325 IX` (2), o 325ix dos anos 1980, que casa com a regra do iX elétrico;
- `MOTO GUZZI CALIFORNIA EV` (12), moto a combustão dos anos 1990;
- `BYD F0`, `G3` e `F6` (8), carros a combustão que a BYD vendeu por volta de
  2010, pegos pela regra "toda BYD é elétrica".

São cerca de 2.350 veículos a mais entre os 445 mil elétricos da base por modelo,
0,5% deles. Corrigir é mexer em `dados/modelos.csv`, que muda a conciliação, e
por isso fica como item próprio.

## 4. Fechar o furo de jan/2022 e esticar a série para trás

Dois buracos distintos:

- **jan/2022** está excluído porque o arquivo publicado era idêntico ao de
  dez/2021 (ver `resultados/LEIAME.md`). Vale checar se a SENATRAN republicou o
  arquivo desde então; se não, o furo é da fonte e fica documentado como está.
- **A série começa em jun/2020.** O CKAN tem mensal desde 2013, mas até 2015
  parte dos arquivos está em `.rar`, que o pacote não abre. Suportar `.rar`
  (via `rarfile` + `unrar`, ou convertendo à mão) levaria a série a 2016 ou
  2013. Para a tendência de eletrificação, 2020 em diante provavelmente basta —
  antes disso a frota eletrificada é residual. Item de baixa prioridade.

## 5. Normalizar marca — feito, com resíduo

Dois problemas, e o menor deles era o das grafias.

**O primeiro era de posição.** O primeiro elemento de "Marca Modelo" não é sempre
a marca: pode ser marcador de importação (`I/`, `IMP/`), a montadora que montou o
veículo no Brasil (`JTA/SUZUKI EN125 YES`) ou o tipo do veículo, em reboque e
máquina (`SR/RANDON SR CA`, `M.A./MASSEY-FERGUSON`, `MR/CAT 416`). Só `I/` e
`IMP/` eram tratados, então 4,58 milhões de veículos tinham como "marca" um
`R`, `SR` ou `REB`. Tratados os prefixos, aparecem os fabricantes que estavam
escondidos: RANDON com 500.746, FACCHINI 246.774, GUERRA 138.320, LIBRELATO
132.229, NOMA 90.997.

A extração também passou a ler tudo o que vem antes da barra, e não até o
primeiro espaço, que é o que o Power Query já fazia — `HARLEY DAVIDSON/XL883N`
dava "HARLEY". Python e painel divergiam.

**O segundo são as grafias**, em `src/eletromobilidade/dados/marcas.csv`
(33 equivalências conferidas à mão). As maiores:

| Marca canônica | Frota | Grafias unidas |
|---|---:|---|
| VOLKSWAGEN | 21.953.416 | VW, VOLKS, VOLKSWAGEN |
| CHEVROLET | 16.500.963 | GM, CHEVROLET, CHEV |
| MERCEDES-BENZ | 2.363.055 | M.BENZ, MBENZ, MERCEDES, M.BENZ313CDI, MERCEDES BENZ |
| MITSUBISHI | 833.802 | MMC, MITSUBISHI |
| SUZUKI | 837.461 | SUZUKI, JTA-SUZUKI |
| CHERY | 420.677 | CAOACHERY, CHERY |
| IVECO | 274.424 | IVECO, IVECOFIAT |
| ROYAL ENFIELD | 112.061 | RE, ROYAL |
| HARLEY-DAVIDSON | 91.372 | HARLEY DAVIDSON, H.DAVIDSON, HARLEY-DAVIDSON |

Na dimensão do painel, 118 marcas viraram 110. O ganho grande não está aí: está
na base completa, onde Chevrolet estava partida em três linhas e Mercedes em
cinco.

**O resíduo, que é real.** A estimativa de "uma tarde" valia para as 118 marcas
do recorte eletrificado. A base completa tem cerca de 4,7 mil grafias distintas,
e normalizar todas à mão não se paga — a cauda é marca de verdade, grafada uma
única vez. O que existe agora é fila ordenada: `processar` lista as grafias que
*parecem* variante de outra (modelo colado na marca, pontuação a mais), por frota
decrescente. São 310, e a maior é `RANDONSP` com 32.547 veículos. Duas ordens de
grandeza abaixo do que já foi resolvido, e por isso item de baixa prioridade
daqui para frente.

O que o heurístico não acha, e que só sai a olho, é abreviação sem parentesco no
texto: `GM` para Chevrolet, `MMC` para Mitsubishi, `LR` para Land Rover. Essas
entraram pelo conhecimento de mercado, uma a uma, e é assim que as próximas
entram.

**Agrupamento por fabricante não foi feito.** `marca` é marca comercial:
CHEVROLET e GMC seguem separadas, como VOLVO e GEELY, como CHERY e OMODA. Somar
por grupo econômico pede outra coluna e outra tabela, com decisão de fronteira
em cada caso — e errar isso é pior que não ter.

## 6. Publicar a tabela longa por classe

O Power BI hoje despivota `combustivel_municipio` em Power Query (ver
[`pbi/powerquery/fFrotaCombustivel.m`](../pbi/powerquery/fFrotaCombustivel.m)).
Funciona, mas põe lógica de modelagem fora do Python, onde não há teste.
Publicar `frota_classe_municipio.parquet` já no formato longo (mês × município ×
classe × frota) tiraria 30 linhas de M e mudaria a consulta para uma leitura
direta. Vale fazer quando o `.pbix` estiver estável — não antes, para não mexer
em duas pontas ao mesmo tempo.

## 7. Outras tabelas da SENATRAN

`municipio_tipo`, `uf_tipo`, `ano_fabricacao`, `tipo_especie_eixos`, `potencia`,
`restricao`, `cor`, `cep` são reconhecidas pelo coletor e não processadas.
Nenhuma cruza com combustível, então nenhuma responde pergunta de
eletromobilidade por si. `potencia` (`E_`) é a mais promissora: potência cruzada
com município dá uma proxy de porte da frota. Só depois do resto.

---

# O que a base sustenta

Critério de qualidade: o que está medido, o que é indício e o que não se pode
afirmar a partir destes dados. Vale para qualquer uso — o roteiro não presume
formato nem destino de entrega.

## O que já está disponível para citar

Base por combustível, setembro de 2026, Brasil:

| | |
|---|---:|
| Frota total registrada | 136.424.856 |
| Frota eletrificada | 1.330.703 |
| Participação | 0,98% |
| Elétricos (BEV) | 484.407 |
| Híbridos plug-in (PHEV) | 83.987 |
| Híbridos convencionais (HEV) | 762.296 |
| Recarregáveis (BEV + PHEV) | 568.394 |
| Célula de combustível | 13 |
| Eletrificados por mil habitantes | 6,21 |

Série de jun/2020 a set/2026, 75 meses, por município, UF e Brasil. No primeiro
mês da série a frota eletrificada era de 41.332 veículos, 0,04% da frota — um
crescimento de **32 vezes em pouco mais de seis anos**, contra 26% de aumento da
frota total no mesmo período. Em dez/2020 eram 54.526 (0,05%), se a comparação
precisar fechar em ano cheio.

Os dois números vêm da mesma base (combustível). Não compare o início da série
pela base por modelo com o fim pela base por combustível: elas medem a
eletrificação de formas diferentes e a razão entre as duas é de 0,82.

Concentração: São Paulo tem 371.659 eletrificados (28% do total nacional), mas o
Distrito Federal lidera em intensidade, com 376 eletrificados por 10 mil
veículos contra 103 de São Paulo e 98 da média nacional. Por habitante a
distância é maior: 28,9 por mil no Distrito Federal, 8,7 em Santa Catarina, 8,0
em São Paulo e 6,2 no Brasil. A população é a estimativa de 2026 do IBGE.

Composição por tipo de veículo, pela base por modelo: 92,8% da frota
eletrificada é leve e 6,9% é moto. Entre os elétricos a bateria a moto é 16,9%
— e era metade, 48,6%, em dez/2020. Cite a parte, não a contagem: a base por
modelo acha 18% menos eletrificados que a por combustível.

## Quatro ressalvas que acompanham estes números em qualquer uso

**Frota é estoque registrado, não emplacamento.** A variação mensal é saldo —
entradas menos baixas, mais correção de cadastro. Escrever "vendas" ou
"licenciamentos" a partir desses números é erro material. A base também inclui
veículos que já não circulam e nunca foram baixados; é característica do
RENAVAM.

**A divisão entre plug-in e híbrido convencional só vale pela base por
combustível.** A inferência por nome de modelo superestima plug-in em 4,5 vezes
e subestima híbrido convencional em 2,8 — ver a conciliação em
[`pbi/MODELO.md`](../pbi/MODELO.md). Os dois somados ficam próximos do correto,
o que mostra que o erro é de classificação entre as duas classes.

**Duas classes não existem no começo da série.** O código de combustível
plug-in só aparece no RENAVAM em **abr/2022**, e o de célula de combustível em
**nov/2022**. Antes disso a contagem é zero, e zero aqui é ausência de código,
não de veículo: `frota_hibrido` não cai quando o plug-in surge, ou seja, os
plug-in anteriores seguem contados como híbrido. Série de PHEV desde 2020 mostra
um zero falso seguido de salto artificial, e o HEV antes de abr/2022 está
inflado pelos plug-in. Para trajetória longa, use a frota eletrificada total ou
BEV; a separação PHEV/HEV só é comparável de abr/2022 em diante. Ambas as
classes estão marcadas em `resultados/qualidade_combustivel.csv`.

**3,6% da frota não tem combustível aproveitável no cadastro.** A fração sobe de
3,17% no início da série para 3,64% em set/2026 (coluna `sem_informacao` na
tabela de qualidade). É limite do RENAVAM, não erro de leitura, e é o piso de
incerteza de qualquer participação calculada sobre a frota total.
