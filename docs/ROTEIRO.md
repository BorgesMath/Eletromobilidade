# Roteiro

Estado em 19/10/2026. O pipeline Python está fechado e testado (171 testes); a
camada do Power BI está especificada em [`pbi/`](../pbi/MODELO.md) e o `.pbix`
ainda precisa ser montado. O que falta está abaixo, em ordem de valor.

As tabelas de `resultados/` ainda são as da execução de 13/10, anterior à
normalização de marca: as colunas novas entram na próxima rodada de `processar` e
`publicar`, que precisa dos arquivos da SENATRAN em `data/raw` (não versionados).

## 1. Código IBGE e nome próprio de município

**Por que primeiro.** Destrava o mapa municipal e o cruzamento com população do
IBGE — isto é, "eletrificados por mil habitantes", que é a medida que uma
política de recarga precisa. Hoje o município é identificado só por
`municipio_norm` (caixa alta, sem acento), e a página 2 do relatório não tem
mapa municipal por causa disso.

**O que fazer.** Uma tabela de referência município → código IBGE em
`src/eletromobilidade/dados/municipios.csv`, casada por `municipio_norm` +
`uf_sigla`, publicada como dimensão em `resultados/`. São 5.581 chaves na base
contra 5.570 municípios do IBGE — a diferença são os três pseudo-municípios
(`SEM INFORMACAO`, `NAO IDENTIFICADO`, `NAO SE APLICA`) mais casos de grafia.
O casamento por nome normalizado vai deixar resíduo; ele precisa de teste que
falhe quando sobrar município sem código.

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

**Por que.** É a lacuna que mais pesa numa nota técnica. Hoje "frota
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
fora concentram justamente moto, scooter e ônibus, que é o número que falta para
a nota técnica.

Então a tabela de regras de tipo continua necessária, mas o escopo encolheu: em
vez de classificar 613 modelos do zero, basta classificar o resíduo não casado e
usar o PBE como verificação de quem já se sabe leve. Combinar com `G_`
(`tipo_especie_eixos`) como total de controle por município, do mesmo jeito que a
base por combustível concilia a base por modelo, transformaria a inferência em
erro medido — e é isso que torna o número por tipo defensável num documento.

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
em cada caso — e errar isso num documento do MME é pior que não ter.

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

# Entrega para o MME

O painel é meio, não fim. A entrega é um documento no padrão SEI, e ele depende
de três decisões que ainda não estão tomadas:

**Gênero.** Nota técnica propositiva, nota informativa de subsídio a autoridade,
ou despacho de contribuições a plano de outro órgão — são três estruturas
diferentes e a escolha muda o documento inteiro, não só o cabeçalho.

**Destinatário e finalidade.** Subsídio a reunião, instrução de processo,
contribuição ao PDE ou ao PLANTE, resposta a proposição legislativa. Define o
nível de detalhe metodológico: numa nota informativa as ressalvas vão em uma
frase; numa nota técnica que embasa decisão, vão em seção própria.

**Recorte.** Frota eletrificada nacional e sua trajetória? Concentração
territorial? Comparação entre as duas bases como avaliação da qualidade do dado
público? Cada um usa uma parte diferente do que já está pronto.

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
| Célula de combustível | 4 |

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

## Duas ressalvas que precisam entrar em qualquer documento

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
