# Páginas do relatório

Cinco páginas. A forma de cada visual foi escolhida pela **função do dado** —
magnitude, identidade, polaridade, um número de manchete, mudança no tempo — e a
cor depois, pela função que ela cumpre. Tema em [`tema.json`](tema.json).

## Regras que valem em todas as páginas

**Segmentações numa única faixa no topo**, acima dos visuais, nunca na laterais
de cada gráfico: período (`dCalendario[Mês/Ano]`), região, UF, classe. Nada de
segmentação de município — são 5.574 membros; use a busca da tabela.

**Nunca dois eixos de valor no mesmo visual.** Frota e participação têm escalas
incomparáveis (milhões contra 1%). Quando os dois precisam aparecer, são dois
visuais, não um com eixo secundário.

**Rótulo de dados direto é obrigatório onde há série colorida.** Três das oito
cores do tema (aqua, amarelo, magenta) ficam abaixo de 3:1 contra a superfície
clara — passam em todos os testes de distinção, mas não podem carregar a
identidade sozinhas. Rótulo visível ou a tabela equivalente na mesma página
resolve. Não é opcional.

**Legenda sempre presente com duas séries ou mais**, e nenhuma com uma só — o
título do visual já nomeia a série.

**A cor segue a entidade, nunca a posição no ranking.** Elétrico é o slot 1 em
toda página; filtrar UF não repinta as classes que sobraram.

**Toda página traz o mês de referência à vista**, via
`[Rótulo do mês de referência]`. Num painel de estoque é a diferença entre ler
certo e ler errado.

---

## 1. Panorama — Brasil

A página de abertura. Responde "quanto é, e está crescendo quanto".

| Visual | Forma | Por quê | Cor |
|---|---|---|---|
| Frota eletrificada | **Número de destaque** (≥48px) | É o número que o painel lidera. Uma barra só não é gráfico. | tinta primária, sem cor de série |
| Subtítulo do destaque | texto | `[Rótulo do mês de referência]` | tinta secundária |
| Elétrico · Plug-in · Híbrido · Participação | **Faixa de 4 cartões** (valor + variação a.a. + minigráfico) | Quatro números de manchete. Barra agrupada aqui seria desperdício. | valor em tinta; variação em verde/vermelho de estado, com ícone e rótulo |
| Frota eletrificada, jun/2020–set/2026 | **Linha**, série única | Tendência no tempo | slot 1 (azul), 2px, sem legenda |
| Composição por classe no tempo | **Coluna empilhada** por mês, 4 classes | Parte-todo que muda ao longo do tempo. Mostra crescimento e composição no mesmo visual. | categórica, slots 1 a 4, ordem fixa de `dClasse[ordem]`, folga de 2px entre segmentos |
| Participação eletrificada | **Linha**, série única | Mesma tendência, outra escala — por isso visual separado | slot 1 |
| Saldo mensal da frota eletrificada | **Coluna divergente** em torno do zero | Acima/abaixo de uma linha de base é polaridade | divergente azul ↔ vermelho, cinza no meio |

Quatro séries na coluna empilhada é o limite confortável: a partir do quarto
slot amarelo e laranja dividem a tela, o que torna o rótulo direto obrigatório —
já é a regra da página. Célula de combustível (4 veículos no Brasil) não entra
como quinta série; fica na tabela.

**Nota de leitura obrigatória no pé da página:** "Saldo mensal é variação do
estoque registrado no RENAVAM — entradas menos baixas e correções de cadastro.
Não é emplacamento nem venda."

---

## 2. Território — UF e município

| Visual | Forma | Por quê | Cor |
|---|---|---|---|
| Eletrificados por 10 mil veículos, por UF | **Mapa coroplético** | Magnitude sobre geografia | **sequencial** azul, do claro ao escuro |
| Frota eletrificada — 15 maiores UF | **Barra horizontal** ordenada | Comparar magnitude; nome de UF cabe melhor na horizontal | sequencial azul, ponta arredondada de 4px ancorada na linha de base |
| Todas as 27 UF | **Tabela** (frota, total, participação, por mil habitantes, variação a.a.) | Mais de sete linhas que todas importam | tinta; formatação condicional na participação com a rampa sequencial |
| Eletrificados por 10 mil veículos, por município | **Mapa de forma** com a malha municipal do IBGE, localizado por `dLocalidade[cod_municipio_ibge]` | Magnitude sobre geografia, no grão em que se decide onde pôr recarga | sequencial azul, a mesma rampa do mapa por UF |
| 50 maiores municípios | **Tabela** com busca (nome oficial, UF, frota eletrificada, frota total, por 10 mil veículos, por mil habitantes) | Lista para ler o número, que o mapa só mostra em cor | tinta |

Os mapas usam **taxa, não contagem**. Mapa de frota absoluta por UF é mapa de
população: São Paulo ganha sempre e o visual não informa nada. Com
`[Eletrificados por 10 mil veículos]` aparece o que interessa — o Distrito
Federal tem 376 por 10 mil contra 103 de São Paulo.

**O mapa municipal depende do código IBGE**, e só existe por isso: a malha do IBGE
identifica cada polígono pelo código de 7 dígitos (`codarea`, o mesmo número de
`cod_municipio_ibge`, em texto), nunca pelo nome. A malha em TopoJSON, 1,4 MB,
vem da API do IBGE —
`https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&intrarregiao=municipio&qualidade=minima`
— e entra no visual como mapa personalizado. Duas ressalvas, as duas visíveis na
página:

- A malha tem 5.570 polígonos. Falta Boa Esperança do Norte (MT), instalado
  depois dela; os 686 veículos dele aparecem na tabela e não no mapa.
- Em município de frota pequena, a taxa oscila com um ou dois veículos e o mapa
  acende onde não há tendência nenhuma. Por isso a tabela, com a frota absoluta,
  fica ao lado do mapa e não é opcional.

**Por veículo e por habitante respondem coisas diferentes**, e as tabelas trazem
as duas. Por 10 mil veículos mede quanto da frota já é eletrificada; por mil
habitantes mede a densidade da frota eletrificada na população, que é o que
dimensiona recarga. Um município de frota grande para a população aparece bem na
segunda e mal na primeira. A taxa por habitante só se compara no tempo dentro da
mesma base de população: a de antes de 2022 é projeção do Censo 2010 (ver
[`MODELO.md`](MODELO.md#outras-limitações-conhecidas)).

As tabelas são também o **alívio de contraste** exigido pela paleta.

---

## 3. Modelos e marcas

**Esta página inteira carrega uma tarja de advertência no topo**, porque os
dados por baixo dela têm duas limitações sérias:

> Base por modelo: apenas dez/2020 e set/2026. A tecnologia é inferida do nome
> do modelo e **não separa híbrido plug-in de híbrido convencional** (razão de
> 4,5 e 0,36 contra o campo combustível). Use esta página para *quais modelos*,
> *de que marca* e *de que ano* — nunca para quantos de cada tecnologia.

| Visual | Forma | Por quê | Cor |
|---|---|---|---|
| Modelos distintos · Marcas · Idade média · % importados | **Faixa de 4 cartões** | Números de manchete da base por modelo | tinta |
| 20 maiores modelos | **Barra horizontal** ordenada | Magnitude; nome de modelo é longo | sequencial azul |
| Marca × classe | **Matriz** | Duas dimensões e um valor | tinta, com barras de dados na célula |
| Frota eletrificada por ano de fabricação | **Coluna** | Magnitude sobre escala ordenada | sequencial azul |
| Nacional × importado | **Barra empilhada** única, 2 séries | Parte-todo de duas classes. Rosca de duas fatias é pior. | slots 1 e 2, rótulo direto |

Agregue por `marca`, não por `marca_renavam`: a primeira une as grafias da mesma
empresa (`GM`, `CHEVROLET` e `CHEV` viram `CHEVROLET`), a segunda é a grafia
original do RENAVAM e serve para auditar. A normalização cobre as grafias
conferidas à mão, então uma marca de frota pequena ainda pode aparecer dividida.

---

## 4. Conciliação — auditoria do método

A página que torna o painel defensável. Mede o erro de inferir tecnologia pelo
nome do modelo, comparando com o campo combustível do mesmo mês e recorte.

| Visual | Forma | Por quê | Cor |
|---|---|---|---|
| Classe × (combustível, modelo, diferença, razão) | **Matriz** | Quatro números por classe lado a lado: é tabela, não gráfico | tinta; razão com 3 decimais |
| Razão modelo/combustível por classe | **Barra divergente centrada em 1,0** | Acima/abaixo de uma linha de base é polaridade, e 1,0 é a linha | divergente azul ↔ vermelho, cinza em 1,0 |
| Combustível → modelo, por classe | **Dumbbell** | Dois valores por item, antes e depois | um matiz, dois tons |
| Erro da classificação por UF | **Mapa coroplético** ou barra ordenada | Onde a inferência vai pior | sequencial, mais escuro = mais erro |
| Modelos a revisar | **Tabela** de `fModelosClassificados` com `revisar = TRUE` | Fila de trabalho das regras de `dados/modelos.csv` | tinta |

A barra divergente em torno de 1,0 é o visual que conta a história: plug-in
dispara para a direita (4,51), híbrido convencional afunda para a esquerda
(0,36), e os dois **somados** voltam para perto de 1 — prova de que o erro é de
classificação entre as duas classes, não de cobertura.

---

## 5. Cobertura e método

| Visual | Forma | Por quê | Cor |
|---|---|---|---|
| Ano × mês, por base | **Matriz de calor** | Grade de magnitude/estado | **estado**: presente, ausente, ajustado — cada um com ícone e rótulo, nunca cor sozinha |
| Meses na série · Excluídos · Com ajuste · Linhas lidas | **Faixa de 4 cartões** | Números de manchete da cobertura | tinta |
| `fCobertura` completa | **Tabela** (arquivo, linhas, frota total, ajuste, incluído) | Registro auditável, arquivo por arquivo | tinta |
| Fontes, classes e limitações | **Caixa de texto** | Texto é texto | tinta secundária |

A matriz de calor mostra os dois buracos conhecidos: a série começa em jun/2020
e **falta jan/2022**. Deixar o mês ausente visível é o ponto do visual — as
medidas não interpolam, e o painel não deve fingir que o dado existe.

O texto de fechamento reproduz, resumidas, as ressalvas de
[`MODELO.md`](MODELO.md): frota é estoque e não emplacamento; a base inclui
veículos que não circulam mais; a inferência por modelo não separa plug-in de
HEV; ainda não há população por município, então as taxas são por frota.

---

## Ordem de construção

Páginas 1 e 5 primeiro. A 1 porque é a que valida o modelo contra os números de
`MODELO.md`; a 5 porque é curta e porque ter a cobertura à vista evita conclusão
errada ao desenhar as outras três. Depois 2, 4 e 3 — a 3 é a que depende de mais
ressalvas e a que menos dado tem hoje.
