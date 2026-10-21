// fPopulacao — população residente estimada (IBGE), por mês e município
//
// Fonte: resultados/combustivel_municipio.parquet, colunas populacao e ano_populacao
// Grão de saída: mês × município (417.765 linhas)
//
// Fato à parte, e não coluna de fFrotaCombustivel: aquele fato é longo, uma
// linha por classe, e a população repetida em cada classe somaria seis vezes.
//
// Tudo vem pronto do Python, inclusive qual estimativa vale em cada mês
// (ano_populacao: 2022 e 2023 usam a de 2024) e a regra que evita somar duas
// vezes a população de Pitangueiras nos meses em que o distrito de Ibitiúva
// aparece ao lado dela. Aqui só se descartam as linhas sem população: os
// pseudo-municípios e esse distrito.
//
// A estimativa muda de base em 2022: até 2021 projeta o Censo 2010, de 2022 em
// diante parte do Censo 2022. Ver a medida [População] em dax/medidas.dax.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\combustivel_municipio.parquet")
    ),
    ComPopulacao = Table.SelectRows(Fonte, each [populacao] <> null),
    Tipos = Table.TransformColumnTypes(
        ComPopulacao,
        {
            {"data_referencia", type date},
            {"uf_sigla", type text},
            {"municipio_norm", type text},
            {"cod_municipio_ibge", Int64.Type},
            {"ano_populacao", Int64.Type},
            {"populacao", Int64.Type}
        }
    ),
    ComChave = Table.AddColumn(
        Tipos,
        "chave_localidade",
        each ChaveLocalidade([cod_municipio_ibge], [uf_sigla], [municipio_norm]),
        type text
    ),
    Final = Table.SelectColumns(
        ComChave,
        {"data_referencia", "chave_localidade", "ano_populacao", "populacao"}
    )
in
    Final
