# eletromobilidade (db-demob)

Base de eletromobilidade construída a partir da frota de veículos da SENATRAN
(RENAVAM): quantos veículos elétricos, híbridos plug-in e híbridos há em cada
município, UF e no Brasil, mês a mês, tratada, conferida e documentada. O
produto são as tabelas de [`resultados/`](resultados/LEIAME.md).

## Fontes

| Fonte | O que entra | Como é usada |
|---|---|---|
| SENATRAN, frota por UF, município e **combustível** (`D_`, mensal, [gov.br](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026)) | Contagem por rótulo de combustível do RENAVAM | Base por combustível: a série mensal, jun/2020 a set/2026 |
| SENATRAN, frota por UF, município, **marca/modelo** e ano de fabricação (`I_`, [CKAN](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907)) | Texto "Marca Modelo", sem combustível | Base por modelo: tecnologia inferida do nome; dez/2020 e set/2026 |
| IBGE, [API de localidades](https://servicodados.ibge.gov.br/api/docs/localidades) | Código e nome oficial dos 5.571 municípios | Identidade do município |
| IBGE, Estimativas de População ([SIDRA 6579](https://sidra.ibge.gov.br/tabela/6579)) | População de 1º de julho, por município | Eletrificados por mil habitantes |
| Inmetro, PBE Veicular (PDF do ciclo) | Propulsão declarada pelo fabricante, versão por versão | Auditoria da classificação por modelo e tipo de veículo leve |
| ABVE, [BI Frotas](https://abve.org.br/bi-frotas/) | Vendas por modelo e tecnologia | Validação externa, feita uma vez ([`docs/ROTEIRO.md`](docs/ROTEIRO.md), item 8) |

Os arquivos da SENATRAN não vão para o repositório; as tabelas do IBGE e do
Inmetro entram como instantâneos versionados em
[`src/eletromobilidade/dados/`](src/eletromobilidade/dados/README.md).

## Arquitetura

```
data/raw/         arquivos da SENATRAN, como baixados        (fora do git)
   │  eletromobilidade baixar
   ▼
src/eletromobilidade/   coleta, leitura, classificação, conciliação
   │  eletromobilidade processar       └─ dados/  tabelas de referência e regras
   ▼
data/processed/   todas as tabelas, Parquet e CSV            (fora do git)
   │  eletromobilidade publicar
   ▼
resultados/       painéis, auditorias, LEIAME e DICIONARIO   (versionado)
```

| Pasta | O que tem | Leia |
|---|---|---|
| [`src/eletromobilidade/`](src/eletromobilidade/README.md) | O pacote Python: CLI, pipeline, qualidade dos arquivos, conciliação | Uso, módulos, saídas |
| [`src/eletromobilidade/dados/`](src/eletromobilidade/dados/README.md) | Regras e tabelas de referência: combustível, modelo, tipo, marca, município, população, PBE | Como cada coisa é classificada e por quê |
| [`resultados/`](resultados/LEIAME.md) | O que o projeto publica. `LEIAME.md` e `DICIONARIO.md` são gerados por `publicar` | Cobertura e colunas |
| [`tests/`](tests/README.md) | Testes do pacote e das tabelas publicadas | Como rodar |
| [`docs/`](docs/README.md) | Roteiro e apresentações | O que falta e o que a base sustenta |
| [`data/`](data/README.md) | Arquivos brutos, cache e saídas locais | Layout |

**Toda regra mora no Python.** O que decide se um veículo é eletrificado está em
`src/`, onde um teste pega a mudança. Quem consome `resultados/` apresenta e
agrega, sem reclassificar.

## Premissas

**Duas bases independentes, conciliadas.** A base por combustível usa o campo
combustível do RENAVAM: é a contagem oficial e tem série mensal. A base por
modelo infere a tecnologia do nome do modelo, porque o arquivo de marca/modelo
não traz combustível: dá marca, modelo, ano de fabricação e tipo de veículo. A
conciliação compara as duas mês a mês e recorte a recorte.

**Frota é estoque registrado, não emplacamento.** A variação mensal é saldo, não
venda. A baixa quase não aparece: os eletrificados leves fabricados até 2018 eram
12.298 em dez/2020 e 12.317 em set/2026.

**Eletrificado é elétrico, plug-in, híbrido e célula de combustível.** O híbrido
leve (12 V ou 48 V) fica fora, em coluna própria. O PBE do Inmetro, que registra
esses carros como combustão, sustenta a decisão.

**O município é o código IBGE, nunca o nome.** A SENATRAN troca a grafia de seis
municípios no meio da série (`EMBU` vira `EMBU DAS ARTES`).

**Classificação por regra explícita, sem semelhança aproximada.** Cada regra é
uma linha de CSV com nota, cada armadilha é um caso de teste, e o que não casa
vai para fila de revisão, não para palpite.

**A série começa em jan/2020.** O arquivo por combustível falta de jan a
mai/2020, então ela começa de fato em jun/2020. A base por modelo tem só dez/2020
e set/2026, por decisão: ampliar seria a parte cara e inferencial.

## Resultados

Base por combustível, set/2026, Brasil:

| | |
|---|---:|
| Frota total registrada | 136.424.856 |
| Frota eletrificada | 1.330.703 (0,98%) |
| Elétricos (BEV) | 484.407 |
| Híbridos (HEV + PHEV pelo campo combustível) | 846.283 |
| Eletrificados por mil habitantes | 6,21 |

Em jun/2020 eram 41.332 eletrificados (0,04% da frota): 32 vezes mais em seis
anos, contra 26% de aumento da frota total. São Paulo concentra 28% do total; o
Distrito Federal lidera em intensidade, com 28,9 eletrificados por mil
habitantes.

**Conciliação, set/2026, UFs válidas** (base por modelo / base por combustível):

| | Combustível | Modelo | Razão |
|---|---:|---:|---:|
| Elétrico | 395.132 | 377.482 | 0,96 |
| Híbrido plug-in | 79.245 | 357.041 | 4,51 |
| Híbrido convencional | 709.697 | 260.572 | 0,37 |
| Híbridos + híbridos leves do modelo | 788.942 | 735.220 | 0,93 |

As duas bases concordam no elétrico e no total de híbridos; divergem na divisão
entre plug-in e híbrido convencional.

**Validação contra as vendas da ABVE.** O crescimento da frota de leves
eletrificados nas UFs válidas, de dez/2020 a set/2026, pela base por modelo, é
913.861; a ABVE vendeu 927.581 no mesmo período, sem micro-híbridos: −1,5%
(elétrico −0,8%, plug-in −2,2%, híbrido −1,3%). Por marca, BYD, GWM, Toyota,
Omoda Jaecoo e Geely batem a ±0,2%.

O que isso decide: **o rótulo HIBRIDO PLUG-IN do campo combustível pega só 22%
dos plug-ins vendidos**; o resto entra como híbrido. A divisão PHEV × HEV vale
pela base por modelo, não pelo campo combustível.

**Composição por tipo** (base por modelo, set/2026): 92,8% da frota eletrificada
é leve e 6,8% é moto. Entre os elétricos a bateria a moto é 16,9%, e era 66,8% em
dez/2020. Cite a parte, não a contagem: a base por modelo acha 18% menos
eletrificados que a por combustível, e a contagem por tipo herda isso.

### Limitações

1. **Sem tipo de veículo no campo combustível.** A participação eletrificada é
   sobre a frota total, não sobre veículos leves; o tipo só existe na base por
   modelo.
2. **Plug-in e célula de combustível começam tarde no RENAVAM**: o código
   plug-in em abr/2022, o de célula em nov/2022. Antes disso o zero é ausência de
   código. A separação PHEV/HEV pelo campo combustível só se compara de abr/2022
   em diante, e mesmo assim subconta o plug-in.
3. **O campo combustível conta híbrido leve como híbrido** (Fiat "Hybrid" como
   GASOLINA/ALCOOL/ELETRICO), e a base por modelo não. A conciliação mede isso
   em `hibrido_leve_modelo`.
4. **ELETRICO/FONTE INTERNA e FONTE EXTERNA** não têm significado documentado de
   forma inequívoca; os dois contam como elétrico, e o rótulo original fica em
   `frota_combustivel`.
5. **O grupo sem UF** ("Sem Informação", 3,1 milhões de veículos) entra no total
   do Brasil e tem, nos eletrificados, perfil de estoque ainda não emplacado.
   Para comparar com vendas, use as UFs válidas.
6. **3,6% da frota não tem combustível aproveitável** no cadastro. É o piso de
   incerteza de qualquer participação sobre a frota total.
7. **Algumas regras de modelo vêm de conhecimento de mercado**, não do texto
   (Stellantis e Caoa Chery "Hybrid" como híbrido leve, Audi "HIBRIDO" como
   híbrido, Jaecoo 7 como plug-in). Cada caso está anotado na nota da regra.

O que pode e o que não pode ser afirmado com a base está em
[`docs/ROTEIRO.md`](docs/ROTEIRO.md#o-que-a-base-sustenta).

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

eletromobilidade baixar --tabela combustivel --anos 2025 2026
eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 9
eletromobilidade -v processar      # data/raw -> data/processed
eletromobilidade publicar          # data/processed -> resultados/
pytest
```

Todos os comandos e opções: [`src/eletromobilidade/README.md`](src/eletromobilidade/README.md).
