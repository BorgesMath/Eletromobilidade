# Roteiro

Estado em 21/10/2026. O pipeline Python está fechado e testado (220 testes); a
camada do Power BI está especificada em [`pbi/`](../pbi/MODELO.md) e o `.pbix`
ainda precisa ser montado. O que falta está abaixo, em ordem de valor.

As tabelas de `resultados/` estão em dia com o código, regeradas em 21/10 com a
série completa de combustível (76 arquivos) e os dois meses da base por modelo.
Reproduziram a execução de 20/10 com diferença zero em todas as colunas que já
existiam; o que mudou foi a coluna `cod_municipio_ibge` e a dimensão de
município. Regerá-las exige os arquivos da SENATRAN em `data/raw`, que não são
versionados: `baixar`, depois `processar` e `publicar`.

## 1. Código IBGE de município — feito; falta a população

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

**O que falta: população.** É o que dá "eletrificados por mil habitantes", a
medida que uma política de recarga usa e o motivo de este item vir primeiro.
Agora é junção pelo código, sem casar nome nenhum. Antes, uma decisão: Censo
2022, que é contagem mas é um ponto só e tem 5.570 municípios (Boa Esperança do
Norte, MT, foi instalado depois), ou as estimativas anuais do IBGE, que dão série
mas são modeladas.

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

## 3. Tipo de veículo

**Por que.** É a lacuna que mais pesa em qualquer leitura da base. Hoje "frota
eletrificada" soma automóvel, motocicleta, ônibus e caminhão num número só.
Para política de eletromobilidade são coisas diferentes: 484 mil elétricos
viram uma frase muito distinta quando se sabe quanto disso é scooter.

**A dificuldade é real.** A SENATRAN **não publica tabela que cruze tipo com
combustível** — `D_` tem combustível sem tipo, `G_` tem tipo sem combustível.
O único caminho é inferir o tipo do nome do modelo, na base por modelo, do mesmo
jeito que a tecnologia já é inferida.

**É viável mas dá trabalho.** Entre os 613 modelos elétricos de set/2026 há
padrões aproveitáveis — potência em kW no nome (`VAMMO/VMOTO COMFORT 4KW`,
`I/GCX X11 3KW`) marca scooter e ciclomotor; marcas de carroceria
(`ELETRA`, `CRRC`, `BUSSCAR`) marcam ônibus; `R/` e `SR/` já identificam
reboque. Mas nenhuma expressão simples resolve: precisa de tabela de regras
revisada à mão, como `dados/modelos.csv`, com a mesma marcação `revisar` para a
fila de trabalho. Não prometa o número por tipo antes de a tabela existir.

**Meio caminho já está andado, pelo Inmetro.** A auditoria contra o PBE Veicular
(ver o README) traz `pbe_categoria` para **79,1% da frota eletrificada** da base
por modelo: Extra Grande 230.352, Utilitário Esportivo Grande 163.418, Médio
159.645, Sub Compacto 126.734, Grande 123.182, Utilitário Esportivo Compacto
84.529, Picape 12.573.

Falta entender o que isso é e o que não é. `pbe_categoria` é **porte de veículo
leve**, não tipo: não distingue automóvel de comercial leve, e não tem como
distinguir, porque o PBE só ensaia veículo leve. O que ele dá de graça é a outra
ponta — **estar no PBE é prova de que o veículo é leve**. Os 20,9% que ficaram
fora concentram justamente moto, scooter e ônibus, que é exatamente o recorte
que hoje falta.

Então a tabela de regras de tipo continua necessária, mas o escopo encolheu: em
vez de classificar 613 modelos do zero, basta classificar o resíduo não casado e
usar o PBE como verificação de quem já se sabe leve. Combinar com `G_`
(`tipo_especie_eixos`) como total de controle por município, do mesmo jeito que a
base por combustível concilia a base por modelo, transformaria a inferência em
erro medido — e é isso que torna o número por tipo defensável, não só plausível.

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
veículos contra 103 de São Paulo e 98 da média nacional.

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
