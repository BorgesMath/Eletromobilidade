# Dicionário de dados

Gerado por `eletromobilidade publicar` a partir das tabelas publicadas.

## Fontes

| Base | Arquivo da SENATRAN | Onde | Colunas originais |
|---|---|---|---|
| Combustível | `D_Frota_por_UF_Municipio_COMBUSTIVEL_<Mês>_<Ano>.xlsx` (mensal) | Páginas anuais [frota-de-veiculos-{ano}](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026) no gov.br (Ministério dos Transportes/SENATRAN) | UF, Município, Combustível Veículo, Qtd. Veículos |
| Modelo | `I_Frota_por_UF_Municipio_Marca_e_Modelo_Ano_<Mês>_<Ano>.zip` (mensal, ~22 mi de linhas) | Conjunto RENAVAM no [portal de dados abertos](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907) (API CKAN); alguns meses de 2019–2022 também no gov.br | UF, Município, Marca Modelo, Ano Fabricação Veículo CRV, Qtd. Veículos |

Ambos são extrações do RENAVAM: frota **registrada** no mês de referência (inclui
veículos que já não circulam e não foram baixados). UF vem por extenso; sigla,
código IBGE da UF e região são acrescentados pelo pacote (tabela fixa em
`src/eletromobilidade/ufs.py`). O município é identificado pelo nome
(`municipio_norm` + `uf_sigla`); o código IBGE do município ainda não está na base.
Classificação: `src/eletromobilidade/dados/combustiveis.csv` (base por
combustível) e `src/eletromobilidade/dados/modelos.csv` (base por modelo).

## Classes de tecnologia

| Classe | Definição |
|---|---|
| `eletrico` | Tração 100% elétrica (a bateria). Combustível: ELETRICO/FONTE EXTERNA, ELETRICO/FONTE INTERNA, ELETRICO. |
| `hibrido_plug_in` | Híbrido recarregável na tomada (PHEV), incluindo elétricos com extensor de autonomia (REEV). |
| `hibrido` | Híbrido convencional (HEV): bateria recarregada só pelo motor a combustão e pela frenagem regenerativa. |
| `hibrido_leve` | Só na base por modelo. Híbrido leve (12/48 V): o motor elétrico não traciona sozinho. Fora da frota eletrificada. |
| `celula_combustivel` | Elétrico a célula de combustível (hidrogênio). |
| `combustao` | Somente motor a combustão (inclui flex e GNV). |
| `nao_motorizado` | Só na base por modelo. Reboques (R/) e semirreboques (SR/). |
| `sem_informacao` | Sem informação de combustível ou de modelo. |

## Tabelas

### `combustivel_brasil.csv`

Base por combustível: frota por classe, total, eletrificada e participação, Brasil, por mês.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `combustivel_uf.csv`

Idem, por UF.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `combustivel_municipio.parquet`

Idem, por município.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `municipio_norm` | texto | Município sem acentos, em caixa alta. Chave do município junto com uf_sigla. |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `combustivel_eletrificados.parquet`

Base por combustível: rótulos eletrificados por município e mês.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf` | texto | UF como publicada pela SENATRAN (por extenso; inclui 'Sem Informação'). |
| `municipio` | texto | Município como publicado pela SENATRAN. |
| `combustivel` | texto | Rótulo do campo combustível do RENAVAM, como publicado. |
| `qtd_veiculos` | inteiro | Número de veículos registrados. |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `municipio_norm` | texto | Município sem acentos, em caixa alta. Chave do município junto com uf_sigla. |
| `arquivo_origem` | texto | Arquivo da SENATRAN de onde o dado veio. |
| `combustivel_norm` | texto | Rótulo de combustível normalizado (sem acentos, caixa alta, grafias unificadas). |
| `classe` | texto | Classe de tecnologia atribuída (ver a tabela de classes). |
| `eletrificado` | lógico | Verdadeiro para eletrico, hibrido_plug_in, hibrido e celula_combustivel. |
| `origem_classificacao` | texto | 'tabela' (rótulo listado em combustiveis.csv) ou 'regra' (inferido; revisar). |

### `combustiveis_classificados.csv`

Auditoria: rótulos de combustível, classe atribuída e total de veículos.

| Coluna | Tipo | Descrição |
|---|---|---|
| `combustivel` | texto | Rótulo do campo combustível do RENAVAM, como publicado. |
| `combustivel_norm` | texto | Rótulo de combustível normalizado (sem acentos, caixa alta, grafias unificadas). |
| `classe` | texto | Classe de tecnologia atribuída (ver a tabela de classes). |
| `eletrificado` | lógico | Verdadeiro para eletrico, hibrido_plug_in, hibrido e celula_combustivel. |
| `origem_classificacao` | texto | 'tabela' (rótulo listado em combustiveis.csv) ou 'regra' (inferido; revisar). |
| `qtd_veiculos` | inteiro | Número de veículos registrados. |
| `primeiro_mes` | data | Primeiro mês em que o rótulo aparece na série. |
| `ultimo_mes` | data | Último mês em que o rótulo aparece na série. |

### `modelo_brasil.csv`

Base por modelo: frota por classe (inclui plug-in x convencional e híbrido leve), Brasil, por mês.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_hibrido_leve` | inteiro | Veículos da classe hibrido_leve. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_nao_motorizado` | inteiro | Veículos da classe nao_motorizado. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `modelo_uf.csv`

Idem, por UF.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_hibrido_leve` | inteiro | Veículos da classe hibrido_leve. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_nao_motorizado` | inteiro | Veículos da classe nao_motorizado. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `modelo_municipio.parquet`

Idem, por município.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `municipio_norm` | texto | Município sem acentos, em caixa alta. Chave do município junto com uf_sigla. |
| `frota_eletrico` | inteiro | Veículos da classe eletrico. |
| `frota_hibrido_plug_in` | inteiro | Veículos da classe hibrido_plug_in. |
| `frota_hibrido` | inteiro | Veículos da classe hibrido. |
| `frota_hibrido_leve` | inteiro | Veículos da classe hibrido_leve. |
| `frota_celula_combustivel` | inteiro | Veículos da classe celula_combustivel. |
| `frota_combustao` | inteiro | Veículos da classe combustao. |
| `frota_nao_motorizado` | inteiro | Veículos da classe nao_motorizado. |
| `frota_sem_informacao` | inteiro | Veículos da classe sem_informacao. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `frota_eletrificada` | inteiro | Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve). |
| `participacao_eletrificada` | decimal | frota_eletrificada / frota_total (fração entre 0 e 1). |

### `modelo_eletrificados.parquet`

Base por modelo: eletrificados e híbridos leves por município, modelo e ano de fabricação.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf` | texto | UF como publicada pela SENATRAN (por extenso; inclui 'Sem Informação'). |
| `municipio` | texto | Município como publicado pela SENATRAN. |
| `marca_modelo` | texto | Texto 'Marca Modelo' do RENAVAM, como publicado (prefixo I/ = importado). |
| `ano_fabricacao` | inteiro | Ano de fabricação (campo do CRV); nulo quando 'Sem Informação'. |
| `classe` | texto | Classe de tecnologia atribuída (ver a tabela de classes). |
| `regra` | inteiro | Número da linha de modelos.csv que definiu a classe (0 = nenhuma regra; classe padrão combustao). |
| `qtd_veiculos` | inteiro | Número de veículos registrados. |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `municipio_norm` | texto | Município sem acentos, em caixa alta. Chave do município junto com uf_sigla. |
| `arquivo_origem` | texto | Arquivo da SENATRAN de onde o dado veio. |

### `modelos_classificados.parquet`

Auditoria: cada modelo, classe, regra aplicada, total e marcação 'revisar'.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `marca_modelo_norm` | texto | Marca Modelo normalizado (sem acentos, caixa alta). |
| `classe` | texto | Classe de tecnologia atribuída (ver a tabela de classes). |
| `regra` | inteiro | Número da linha de modelos.csv que definiu a classe (0 = nenhuma regra; classe padrão combustao). |
| `qtd_veiculos` | inteiro | Número de veículos registrados. |
| `revisar` | lógico | Verdadeiro para modelo de marca com linha eletrificada que não casou com nenhuma regra. |
| `padrao` | texto | Expressão regular da regra aplicada. |

### `conciliacao_brasil.csv`

Comparação combustível x modelo, Brasil, nos meses presentes nas duas bases.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `total_combustivel` | inteiro | Frota total: pela base por combustível. |
| `total_modelo` | inteiro | Frota total: pela base por modelo. |
| `total_diferenca` | inteiro | Frota total: diferença modelo − combustível. |
| `total_razao` | decimal | Frota total: razão modelo / combustível (nula se combustível = 0). |
| `eletrico_combustivel` | inteiro | Elétricos: pela base por combustível. |
| `eletrico_modelo` | inteiro | Elétricos: pela base por modelo. |
| `eletrico_diferenca` | inteiro | Elétricos: diferença modelo − combustível. |
| `eletrico_razao` | decimal | Elétricos: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_plug_in_combustivel` | inteiro | Híbridos plug-in: pela base por combustível. |
| `hibrido_plug_in_modelo` | inteiro | Híbridos plug-in: pela base por modelo. |
| `hibrido_plug_in_diferenca` | inteiro | Híbridos plug-in: diferença modelo − combustível. |
| `hibrido_plug_in_razao` | decimal | Híbridos plug-in: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_combustivel` | inteiro | Híbridos convencionais: pela base por combustível. |
| `hibrido_modelo` | inteiro | Híbridos convencionais: pela base por modelo. |
| `hibrido_diferenca` | inteiro | Híbridos convencionais: diferença modelo − combustível. |
| `hibrido_razao` | decimal | Híbridos convencionais: razão modelo / combustível (nula se combustível = 0). |
| `hibridos_combustivel` | inteiro | Híbridos plug-in + convencionais: pela base por combustível. |
| `hibridos_modelo` | inteiro | Híbridos plug-in + convencionais: pela base por modelo. |
| `hibridos_diferenca` | inteiro | Híbridos plug-in + convencionais: diferença modelo − combustível. |
| `hibridos_razao` | decimal | Híbridos plug-in + convencionais: razão modelo / combustível (nula se combustível = 0). |
| `eletrificada_combustivel` | inteiro | Frota eletrificada: pela base por combustível. |
| `eletrificada_modelo` | inteiro | Frota eletrificada: pela base por modelo. |
| `eletrificada_diferenca` | inteiro | Frota eletrificada: diferença modelo − combustível. |
| `eletrificada_razao` | decimal | Frota eletrificada: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_leve_modelo` | inteiro | Híbridos leves na base por modelo (sem equivalente na base por combustível). |

### `conciliacao_uf.csv`

Idem, por UF.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `total_combustivel` | inteiro | Frota total: pela base por combustível. |
| `total_modelo` | inteiro | Frota total: pela base por modelo. |
| `total_diferenca` | inteiro | Frota total: diferença modelo − combustível. |
| `total_razao` | decimal | Frota total: razão modelo / combustível (nula se combustível = 0). |
| `eletrico_combustivel` | inteiro | Elétricos: pela base por combustível. |
| `eletrico_modelo` | inteiro | Elétricos: pela base por modelo. |
| `eletrico_diferenca` | inteiro | Elétricos: diferença modelo − combustível. |
| `eletrico_razao` | decimal | Elétricos: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_plug_in_combustivel` | inteiro | Híbridos plug-in: pela base por combustível. |
| `hibrido_plug_in_modelo` | inteiro | Híbridos plug-in: pela base por modelo. |
| `hibrido_plug_in_diferenca` | inteiro | Híbridos plug-in: diferença modelo − combustível. |
| `hibrido_plug_in_razao` | decimal | Híbridos plug-in: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_combustivel` | inteiro | Híbridos convencionais: pela base por combustível. |
| `hibrido_modelo` | inteiro | Híbridos convencionais: pela base por modelo. |
| `hibrido_diferenca` | inteiro | Híbridos convencionais: diferença modelo − combustível. |
| `hibrido_razao` | decimal | Híbridos convencionais: razão modelo / combustível (nula se combustível = 0). |
| `hibridos_combustivel` | inteiro | Híbridos plug-in + convencionais: pela base por combustível. |
| `hibridos_modelo` | inteiro | Híbridos plug-in + convencionais: pela base por modelo. |
| `hibridos_diferenca` | inteiro | Híbridos plug-in + convencionais: diferença modelo − combustível. |
| `hibridos_razao` | decimal | Híbridos plug-in + convencionais: razão modelo / combustível (nula se combustível = 0). |
| `eletrificada_combustivel` | inteiro | Frota eletrificada: pela base por combustível. |
| `eletrificada_modelo` | inteiro | Frota eletrificada: pela base por modelo. |
| `eletrificada_diferenca` | inteiro | Frota eletrificada: diferença modelo − combustível. |
| `eletrificada_razao` | decimal | Frota eletrificada: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_leve_modelo` | inteiro | Híbridos leves na base por modelo (sem equivalente na base por combustível). |

### `conciliacao_municipio.parquet`

Idem, por município.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `uf_sigla` | texto | Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.). |
| `cod_uf_ibge` | inteiro | Código IBGE da UF (2 dígitos). |
| `regiao` | texto | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). |
| `municipio_norm` | texto | Município sem acentos, em caixa alta. Chave do município junto com uf_sigla. |
| `total_combustivel` | inteiro | Frota total: pela base por combustível. |
| `total_modelo` | inteiro | Frota total: pela base por modelo. |
| `total_diferenca` | inteiro | Frota total: diferença modelo − combustível. |
| `total_razao` | decimal | Frota total: razão modelo / combustível (nula se combustível = 0). |
| `eletrico_combustivel` | inteiro | Elétricos: pela base por combustível. |
| `eletrico_modelo` | inteiro | Elétricos: pela base por modelo. |
| `eletrico_diferenca` | inteiro | Elétricos: diferença modelo − combustível. |
| `eletrico_razao` | decimal | Elétricos: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_plug_in_combustivel` | inteiro | Híbridos plug-in: pela base por combustível. |
| `hibrido_plug_in_modelo` | inteiro | Híbridos plug-in: pela base por modelo. |
| `hibrido_plug_in_diferenca` | inteiro | Híbridos plug-in: diferença modelo − combustível. |
| `hibrido_plug_in_razao` | decimal | Híbridos plug-in: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_combustivel` | inteiro | Híbridos convencionais: pela base por combustível. |
| `hibrido_modelo` | inteiro | Híbridos convencionais: pela base por modelo. |
| `hibrido_diferenca` | inteiro | Híbridos convencionais: diferença modelo − combustível. |
| `hibrido_razao` | decimal | Híbridos convencionais: razão modelo / combustível (nula se combustível = 0). |
| `hibridos_combustivel` | inteiro | Híbridos plug-in + convencionais: pela base por combustível. |
| `hibridos_modelo` | inteiro | Híbridos plug-in + convencionais: pela base por modelo. |
| `hibridos_diferenca` | inteiro | Híbridos plug-in + convencionais: diferença modelo − combustível. |
| `hibridos_razao` | decimal | Híbridos plug-in + convencionais: razão modelo / combustível (nula se combustível = 0). |
| `eletrificada_combustivel` | inteiro | Frota eletrificada: pela base por combustível. |
| `eletrificada_modelo` | inteiro | Frota eletrificada: pela base por modelo. |
| `eletrificada_diferenca` | inteiro | Frota eletrificada: diferença modelo − combustível. |
| `eletrificada_razao` | decimal | Frota eletrificada: razão modelo / combustível (nula se combustível = 0). |
| `hibrido_leve_modelo` | inteiro | Híbridos leves na base por modelo (sem equivalente na base por combustível). |

### `qualidade_combustivel.csv`

Arquivos mensais da base por combustível: linhas, total, ajustes e inclusão na série.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `arquivo` | texto | Arquivo mensal da SENATRAN. |
| `linhas` | inteiro | Linhas lidas do arquivo. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `ajuste` | texto | Correção aplicada ao arquivo (vazio se nenhuma). |
| `incluido` | lógico | Se o mês entrou na série (falso para mês idêntico ao anterior). |

### `qualidade_modelo.csv`

Idem para a base por modelo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ano` | inteiro | Ano do mês de referência do arquivo mensal. |
| `mes` | inteiro | Mês de referência (1 a 12). |
| `data_referencia` | data | Primeiro dia do mês de referência (para eixos de tempo). |
| `arquivo` | texto | Arquivo mensal da SENATRAN. |
| `linhas` | inteiro | Linhas lidas do arquivo. |
| `frota_total` | inteiro | Frota total do recorte (todas as classes). |
| `ajuste` | texto | Correção aplicada ao arquivo (vazio se nenhuma). |
| `incluido` | lógico | Se o mês entrou na série (falso para mês idêntico ao anterior). |
