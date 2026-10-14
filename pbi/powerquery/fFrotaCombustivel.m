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
// Linhas com uf_sigla nula recebem "ND". São três pseudo-municípios da
// publicação da SENATRAN — SEM INFORMACAO, NAO IDENTIFICADO, NAO SE APLICA —
// que somam cerca de 2% da frota nacional. Descartá-los faria o painel do
// Brasil não fechar com `combustivel_brasil.csv`.
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
            {"frota_eletrico", Int64.Type},
            {"frota_hibrido_plug_in", Int64.Type},
            {"frota_hibrido", Int64.Type},
            {"frota_celula_combustivel", Int64.Type},
            {"frota_combustao", Int64.Type},
            {"frota_sem_informacao", Int64.Type}
        }
    ),
    UfND = Table.ReplaceValue(Tipos, null, "ND", Replacer.ReplaceValue, {"uf_sigla"}),
    ComChave = Table.AddColumn(
        UfND,
        "chave_localidade",
        each [uf_sigla] & "|" & [municipio_norm],
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
