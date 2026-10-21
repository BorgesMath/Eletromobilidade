// fFrotaCombustivel — fato principal
//
// Fonte: resultados/combustivel_municipio.parquet (417.997 linhas)
// Grão de saída: mês × município × classe de tecnologia
//
// A tabela publicada é larga (uma coluna por classe). Aqui ela é despivotada
// para o formato longo, que é o que permite a dimensão dClasse. As colunas
// derivadas da publicação (frota_total, frota_eletrificada,
// participacao_eletrificada) NÃO são carregadas: viriam em duplicidade com as
// medidas DAX. A soma das seis classes é igual a frota_total linha a linha
// (verificado na série inteira).
//
// A chave do município é o código IBGE (ver ChaveLocalidade). Os três
// pseudo-municípios da SENATRAN — SEM INFORMACAO, NAO IDENTIFICADO, NAO SE
// APLICA — não têm UF nem código e ficam com chave própria, "ND|" e o nome.
// Somam cerca de 2% da frota nacional; descartá-los faria o painel do Brasil
// não fechar com `combustivel_brasil.csv`.
//
// 2.507.982 linhas após o despivotamento; 1.266.245 depois de remover zeros.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\combustivel_municipio.parquet")
    ),
    Tipos = Table.TransformColumnTypes(
        Fonte,
        {
            {"data_referencia", type date},
            {"uf_sigla", type text},
            {"municipio_norm", type text},
            {"cod_municipio_ibge", Int64.Type},
            {"frota_eletrico", Int64.Type},
            {"frota_hibrido_plug_in", Int64.Type},
            {"frota_hibrido", Int64.Type},
            {"frota_celula_combustivel", Int64.Type},
            {"frota_combustao", Int64.Type},
            {"frota_sem_informacao", Int64.Type}
        }
    ),
    ComChave = Table.AddColumn(
        Tipos,
        "chave_localidade",
        each ChaveLocalidade([cod_municipio_ibge], [uf_sigla], [municipio_norm]),
        type text
    ),
    Enxuta = Table.SelectColumns(
        ComChave,
        {
            "data_referencia",
            "chave_localidade",
            "frota_eletrico",
            "frota_hibrido_plug_in",
            "frota_hibrido",
            "frota_celula_combustivel",
            "frota_combustao",
            "frota_sem_informacao"
        }
    ),
    Longa = Table.UnpivotOtherColumns(
        Enxuta,
        {"data_referencia", "chave_localidade"},
        "coluna_classe",
        "frota"
    ),
    ComClasse = Table.AddColumn(
        Longa,
        "classe",
        each Text.AfterDelimiter([coluna_classe], "frota_"),
        type text
    ),
    SemZeros = Table.SelectRows(ComClasse, each [frota] <> 0),
    Final = Table.SelectColumns(
        SemZeros,
        {"data_referencia", "chave_localidade", "classe", "frota"}
    )
in
    Final
