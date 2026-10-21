# Modelo do painel de eletromobilidade

Modelo estrela sobre a pasta [`resultados/`](../resultados/LEIAME.md), que o
pacote Python versiona a cada `eletromobilidade publicar`. O Power BI não lê a
SENATRAN nem a API do CKAN: lê só os arquivos publicados. Coleta, tratamento e
classificação ficam no Python, onde há teste automatizado; o PBI faz
apresentação e agregação.

Modo de armazenamento: **Importação**. Todo o modelo cabe em memória com folga
(cerca de 1,5 milhão de linhas no maior fato) e as fontes são arquivos locais.

## Diagrama

Fatos nas linhas, dimensões nas colunas; `●` é um relacionamento.

```
                                     dCalendario   dLocalidade   dClasse   dModelo
                                      [Data]     [chave_local.]  [classe] [marca_modelo]
                          linhas       ~2.465        5.574           8       935
fFrotaCombustivel      1.266.245         ●             ●             ●
fPopulacao               417.765         ●             ●
fFrotaModelo             195.356         ●             ●             ●         ●
fConciliacao              11.147         ●             ●
fModelosClassificados     70.869         ●                           ●
fCobertura                    78         ●
```

`dCalendario` é marcada como tabela de data.

Todos os relacionamentos são **um para muitos, da dimensão para o fato, com
filtro em direção única**. Nenhum bidirecional: as medidas que precisam
atravessar uma dimensão já usam `REMOVEFILTERS` explícito, o que é mais
previsível que filtro cruzado automático.

## Tabelas

### Fatos

| Tabela | Grão | Linhas | Fonte |
|---|---|---:|---|
| `fFrotaCombustivel` | mês × município × classe | 1.266.245 | `combustivel_municipio.parquet` |
| `fPopulacao` | mês × município | 417.765 | `combustivel_municipio.parquet` (colunas de população) |
| `fFrotaModelo` | mês × município × modelo × ano de fabricação × classe | 195.356 | `modelo_eletrificados.parquet` |
| `fConciliacao` | mês × município | 11.147 | `conciliacao_municipio.parquet` |
| `fModelosClassificados` | mês × modelo normalizado | 70.869 | `modelos_classificados.parquet` |
| `fCobertura` | base × mês | 78 | `qualidade_combustivel.csv` + `qualidade_modelo.csv` |

### Dimensões

| Tabela | Grão | Linhas | Fonte |
|---|---|---:|---|
| `dCalendario` | dia | ~2.465 | tabela calculada em DAX |
| `dLocalidade` | município (código IBGE) | 5.574 | `municipios_dimensao.parquet` |
| `dClasse` | classe de tecnologia | 8 | digitada no Power Query |
| `dModelo` | marca_modelo (com marca e tipo de veículo) | 935 | `modelos_dimensao.parquet` |

### Relacionamentos

| De | Para | Cardinalidade |
|---|---|---|
| `dCalendario[Data]` | `fFrotaCombustivel[data_referencia]` | 1 → * |
| `dCalendario[Data]` | `fPopulacao[data_referencia]` | 1 → * |
| `dCalendario[Data]` | `fFrotaModelo[data_referencia]` | 1 → * |
| `dCalendario[Data]` | `fConciliacao[data_referencia]` | 1 → * |
| `dCalendario[Data]` | `fModelosClassificados[data_referencia]` | 1 → * |
| `dCalendario[Data]` | `fCobertura[data_referencia]` | 1 → * |
| `dLocalidade[chave_localidade]` | `fFrotaCombustivel[chave_localidade]` | 1 → * |
| `dLocalidade[chave_localidade]` | `fPopulacao[chave_localidade]` | 1 → * |
| `dLocalidade[chave_localidade]` | `fFrotaModelo[chave_localidade]` | 1 → * |
| `dLocalidade[chave_localidade]` | `fConciliacao[chave_localidade]` | 1 → * |
| `dClasse[classe]` | `fFrotaCombustivel[classe]` | 1 → * |
| `dClasse[classe]` | `fFrotaModelo[classe]` | 1 → * |
| `dClasse[classe]` | `fModelosClassificados[classe]` | 1 → * |
| `dModelo[marca_modelo]` | `fFrotaModelo[marca_modelo]` | 1 → * |

`fModelosClassificados` não se liga a `dModelo`: a tabela publicada usa
`marca_modelo_norm` (sem acento, caixa alta), que é chave diferente de
`marca_modelo`. Também não se liga a `dLocalidade` — já vem agregada no Brasil.

## Decisões de modelagem

**Um fato no grão de município, e não os três painéis publicados.** A pasta
`resultados/` traz `combustivel_municipio`, `_uf` e `_brasil` já agregados.
Carregar os três criaria o problema clássico de somar níveis diferentes do mesmo
estoque. Carrega-se só o grão mais fino e a agregação sobe pela `dLocalidade`.
Está verificado que isso reproduz os painéis publicados **com diferença zero**,
nos 75 meses, tanto para `frota_total` quanto para `frota_eletrificada`.

**O fato principal é despivotado.** A tabela publicada é larga, uma coluna por
classe. O formato longo é o que permite uma dimensão `dClasse` de verdade — com
rótulo, ordenação e o sinalizador `eletrificado` — em vez de oito medidas
independentes sem nada em comum. Custa 1,27 milhão de linhas (zeros removidos),
irrelevante em Importação.

**`frota_total`, `frota_eletrificada` e `participacao_eletrificada` não são
carregadas.** São derivadas; vêm de medidas DAX. Carregar as duas versões é
convite a divergência quando uma mudar.

**O município é o código IBGE, não o nome.** A SENATRAN troca a grafia de seis
municípios no meio da série — `EMBU` vira `EMBU DAS ARTES` em abr/2022, `GOUVEA`
vira `GOUVEIA` em mar/2024. Com a chave por nome, cada grafia era um membro de
`dLocalidade`, e a série desses municípios aparecia cortada em dois. Com a chave
por código são um membro só, com os 75 meses. O código vem do Python, em toda
tabela municipal (`cod_municipio_ibge`), e a chave é montada por uma função só,
[`ChaveLocalidade`](powerquery/ChaveLocalidade.m), igual na dimensão e nos quatro
fatos que a usam. Para achar um município pelo nome antigo, a busca vai em
`dLocalidade[grafias_senatran]`.

**A população é um fato, não uma coluna da dimensão.** Ela muda de ano para ano,
e qual estimativa vale em cada mês é regra do Python (`ano_populacao`). Como
coluna de `fFrotaCombustivel`, que é longo, repetiria em cada classe e somaria seis
vezes. `fPopulacao` tem uma linha por mês e município, e `[População]` é
semi-aditiva como a frota.

**UF inválida vira `"ND"`, não é descartada.** A SENATRAN publica três
pseudo-municípios — `SEM INFORMACAO`, `NAO IDENTIFICADO`, `NAO SE APLICA` — com
UF nula e, portanto, sem código IBGE. São cerca de 2% da frota nacional. Jogá-los
fora faria o total do Brasil não fechar com `combustivel_brasil.csv`; mantê-los
como membro explícito, com chave `ND|<nome>`, deixa o buraco visível no painel,
que é o comportamento honesto.

**`fConciliacao` fica larga.** Cada métrica existe em quatro versões
(`_combustivel`, `_modelo`, `_diferenca`, `_razao`) e o uso é comparar colunas
lado a lado numa matriz, não cortar por dimensão. Despivotar só complicaria.

**As colunas `*_razao` são recalculadas em DAX.** As publicadas estão corretas
no grão em que foram gravadas, mas média de razões não é razão das somas:
agregá-las por UF ou por região daria número errado. A medida divide os
somatórios.

**O calendário é diário.** `DATEADD` exige datas contíguas. Os fatos só têm o
dia 1º de cada mês; o resto do calendário fica sem correspondência, o que é
esperado. Use sempre a hierarquia Ano > Trimestre > Mês nos visuais.

## Duas ressalvas que mudam a leitura do painel

### 1. Frota é estoque

Cada linha é a frota **registrada** no RENAVAM no mês de referência, não o que
foi emplacado no mês. Dois efeitos:

- Somar meses não dá o ano. Por isso as medidas são semi-aditivas e devolvem o
  último mês com dado do período selecionado. Detalhe em
  [`dax/medidas.dax`](dax/medidas.dax), grupo 1.
- A variação mensal (`[Saldo do mês]`) é saldo: entradas menos baixas, mais
  correção de cadastro. **Não é emplacamento e não é venda.** Escrever "vendas"
  a partir desse número é erro material, em qualquer texto.

A base inclui veículos que já não circulam e nunca foram baixados — é
característica do RENAVAM, não do tratamento.

### 2. A base por modelo não separa plug-in de híbrido convencional

A conciliação de set/2026 no Brasil, que é exatamente para isso que serve:

| Recorte | razão modelo / combustível | leitura |
|---|---:|---|
| frota total | 1,000 | as duas bases cobrem o mesmo universo |
| eletrificada | 0,823 | a inferência por nome acha 18% menos eletrificados |
| elétrico | 0,919 | aceitável |
| **plug-in** | **4,510** | superestima em 4,5 vezes |
| **híbrido (HEV)** | **0,356** | subestima em 2,8 vezes |
| híbridos (plug-in + HEV) | — | somados, o erro quase desaparece |

Os dois erros se cancelam quando somados: o problema é de **classificação entre
plug-in e HEV**, não de cobertura. Nome comercial não diz se o carro recarrega
na tomada — "HYBRID" no fim do modelo pode ser qualquer um dos dois.

**De que lado está o erro, a auditoria do Inmetro dá indício.** Confrontada com a
tabela PBE Veicular, que traz a propulsão declarada pelo fabricante versão por
versão, a classificação por nome tem só 20 modelos e 8.177 veículos marcados
como classe eletrificada que o PBE não registra para aquele modelo
(`pbe_aviso = 'sem_versao_no_pbe'`) — ordem de grandeza nenhuma perto dos 273 mil
plug-ins de diferença entre as duas bases. Isso aponta para o campo combustível
subnotificando PHEV, como o README já supunha, e não para a regra inventando
plug-in. **Indício, não prova:** a cobertura do PBE é de 79% da frota
eletrificada e a chave de junção é marca + modelo, não versão, então ela não vê
toda troca de classe. Até medir isso direito, a regra do painel não muda.

Portanto, no painel:

- a divisão por tecnologia vem **sempre** da base por combustível;
- a base por modelo responde *quais modelos*, *de que marca*, *de que ano* e *de
  que tipo de veículo* — não *quantos de cada tecnologia*;
- o tipo de veículo (`dModelo[tipo_rotulo]`) se lê como **composição**, por
  `[Participação do tipo na frota eletrificada]`. O tipo de um modelo com nome não
  é ambíguo como a tecnologia, mas a base por modelo acha 18% menos
  eletrificados, e a contagem por tipo herda isso;
- `[Frota recarregável]` (elétrico + plug-in), que é o recorte que interessa
  para infraestrutura de recarga, só pode sair da base por combustível.

### Outras limitações conhecidas

- **A população muda de base em 2022.** As estimativas do IBGE até 2021 projetam o
  Censo 2010; de 2022 em diante, o Censo 2022 (2022 e 2023 não têm estimativa e
  usam a de 2024). No Brasil a diferença é de -0,3%, mas 1.709 municípios mudam
  mais de 10% entre a estimativa de 2021 e a de 2024. `[Eletrificados por mil
  habitantes]` de um município comparado através de 2022 mede revisão de
  população junto com frota.
- **Marca normalizada só até onde a tabela alcança.** `dModelo[marca]` já une as
  grafias conferidas à mão (`GM`, `CHEVROLET` e `CHEV` viram `CHEVROLET`;
  `CAOACHERY` vira `CHERY`; `CIVIC`, que é modelo lido como marca, vira `HONDA`),
  por `src/eletromobilidade/dados/marcas.csv`. Grafia fora da tabela segue como
  está: das 110 marcas da dimensão, as conferidas são as que têm frota
  relevante. Para auditar, compare com `dModelo[marca_renavam]`, que é a grafia
  original.
- **Falta jan/2022** na série por combustível (o arquivo publicado era idêntico
  ao de dez/2021). Fica em branco; as medidas não interpolam.
- **A base por modelo tem dois meses** (dez/2020 e set/2026). Não há série
  temporal por modelo.

## Como montar o `.pbix`

Não há `.pbix` versionado: binário em Git não rende revisão nem diff. O arquivo
se monta a partir destes scripts em cerca de vinte minutos.

1. **Parâmetro.** Novo arquivo no Power BI Desktop > Transformar dados >
   Nova consulta > Consulta nula. Editor Avançado, cole
   [`powerquery/00-PastaResultados.m`](powerquery/00-PastaResultados.m), nomeie
   a consulta `PastaResultados` e ajuste o caminho.
2. **Consultas.** Uma consulta nula por arquivo de `powerquery/`, cole o
   conteúdo no Editor Avançado, nomeie **igual ao nome do arquivo** (as medidas
   e as outras consultas referenciam esses nomes). Ordem indiferente.
   `ChaveLocalidade` é função, não tabela: desmarque "Habilitar carga" nela.
3. **Fechar e aplicar.**
4. **`dCalendario`.** Modelagem > Nova tabela, cole
   [`dax/dCalendario.dax`](dax/dCalendario.dax). Renomeie a coluna `Date` para
   `Data`. Marque como tabela de data. Aplique as configurações de coluna
   listadas no fim do arquivo (classificar `Mês` por `Mês (número)` etc.) —
   sem isso os meses saem em ordem alfabética.
5. **Relacionamentos.** Crie os catorze da tabela acima. Confira que todos estão
   em direção única; o Power BI às vezes propõe bidirecional.
6. **Medidas.** Cole as de [`dax/medidas.dax`](dax/medidas.dax) na ordem do
   arquivo. Formate: inteiro com separador de milhar para frota e população,
   porcentagem com 2 decimais para participação, 2 decimais para as taxas por
   mil habitantes, 3 decimais para as razões da conciliação.
7. **Ocultar dos relatórios** todas as colunas de chave: `chave_localidade` nos
   cinco lugares, `classe` nos fatos (use `dClasse[rotulo]`),
   `data_referencia` nos fatos (use `dCalendario`).
8. **Valide** contra a tabela abaixo antes de desenhar qualquer visual.

## Validação

Com o período inteiro selecionado e sem nenhum filtro, estes números têm de
sair exatos. Saem de `resultados/combustivel_brasil.csv`, set/2026.

| Medida | Valor esperado |
|---|---:|
| `[Mês de referência]` | 01/09/2026 |
| `[Frota total]` | 136.424.856 |
| `[Frota eletrificada]` | 1.330.703 |
| `[Frota elétrica]` | 484.407 |
| `[Frota híbrida plug-in]` | 83.987 |
| `[Frota híbrida]` | 762.296 |
| `[Frota recarregável]` | 568.394 |
| `[Participação eletrificada]` | 0,98% |
| `[População]` | 214.211.951 |
| `[Eletrificados por mil habitantes]` | 6,21 |
| `[Meses na série]` | 75 |

E com o mês de set/2026 e a UF de São Paulo:

| Medida | Valor esperado |
|---|---:|
| `[Frota total]` | 36.174.177 |
| `[Frota eletrificada]` | 371.659 |
| `[Participação eletrificada]` | 1,03% |
| `[População]` | 46.179.008 |
| `[Eletrificados por mil habitantes]` | 8,05 |

`[População]` do Brasil é a soma dos municípios, a estimativa de 2026 do IBGE.
Se vier o dobro de algum município, ou a de Pitangueiras somada duas vezes, a
população está sendo lida de `fFrotaCombustivel`, e não de `fPopulacao`.

E o tipo de veículo, na base por modelo em set/2026, por `dModelo[tipo_rotulo]`
(sai de `resultados/modelo_tipo_brasil.csv`):

| `[Participação do tipo na frota eletrificada]` | Valor esperado |
|---|---:|
| Automóvel e comercial leve | 92,83% |
| Moto, scooter e ciclomotor | 6,85% |
| Caminhão | 0,24% |
| Ônibus | 0,08% |

E o teste da chave por código, com o município de Embu das Artes
(`dLocalidade[cod_municipio_ibge] = 3515004`):

| Verificação | Valor esperado |
|---|---|
| `[Frota total]` em set/2026 | 153.787 |
| `[Frota eletrificada]` em set/2026 | 627 |
| `[População]` em set/2026 | 260.113 |
| Linha de `[Frota total]` por mês | contínua de jun/2020 a set/2026, só sem jan/2022; em mar/2022 são 126.441 e em abr/2022, 126.775 |
| `dLocalidade[grafias_senatran]` | `EMBU \| EMBU DAS ARTES` |

Se a linha de Embu das Artes começar em abr/2022, algum fato está montando a
chave pelo nome em vez de chamar `ChaveLocalidade`.

Se `[Frota total]` do Brasil vier menor que 136.424.856, a causa mais provável é
linha descartada no Power Query: os pseudo-municípios não têm UF nem código, e
uma etapa que filtre nulos os leva junto.
