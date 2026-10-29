# Testes

```bash
pytest
```

Os testes do pacote usam arquivos sintéticos no leiaute da SENATRAN
(`conftest.py`) e, para os classificadores, textos reais do campo "Marca Modelo".
Toda armadilha de nome conhecida, e toda regra nova, entra como caso em
`test_modelos.py` ou `test_tipos.py`.

| Arquivo | O que cobre |
|---|---|
| `test_coleta.py` | Links do CKAN e do portal, escolha da fonte, download retomado, arquivo corrompido ou HTML no lugar do arquivo, cache da listagem |
| `test_leitura.py` | Leitura dos arquivos mensais (`.xlsx`, `.csv`, `.zip`), período pelo nome, acentos corrompidos |
| `test_pipeline.py` | Base por combustível e por modelo, conciliação, cache, defeitos de arquivo, meses ausentes, CLI |
| `test_texto_classificacao.py` | Normalização de texto, UF e classificação dos rótulos de combustível |
| `test_modelos.py` | Regras de `dados/modelos.csv` com textos reais, marca e `revisar` |
| `test_tipos.py` | Regras de `dados/tipos.csv` e prioridade do PBE |
| `test_inmetro.py` | Junção e avisos da tabela PBE Veicular |
| `test_municipios.py` | Código IBGE, grafias conferidas contra o IBGE, dimensão de município |
| `test_populacao.py` | Estimativa usada em cada ano, distrito de Ibitiúva, soma de UF e Brasil |
| `test_publicacao.py` | `publicar`, o `LEIAME.md` e o `DICIONARIO.md` |

**Os testes `test_resultados_*`** (em `test_municipios.py`, `test_populacao.py`
e `test_tipos.py`) leem as tabelas versionadas em `resultados/`: todo município
com UF tem código, toda linha tem população uma vez por mês, nenhuma regra de
tipo contradiz o PBE, a frota sem tipo é residual. Depois de mudar uma regra,
eles só refletem a mudança quando `processar` e `publicar` rodam de novo.
