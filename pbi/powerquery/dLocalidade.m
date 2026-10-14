// dLocalidade — dimensão de município, UF e região (denormalizada)
//
// Fonte: resultados/combustivel_municipio.parquet
// Grão: município (5.581 membros, incluindo 3 pseudo-municípios da SENATRAN)
//
// Uma dimensão só, achatada, em vez de dMunicipio → dUF → dRegiao. Hierarquia
// natural, cardinalidade baixa, e evita snowflake sem ganho nenhum.
//
// É construída a partir da base por combustível porque ela é a mais ampla: as
// localidades de modelo_eletrificados (4.975) e de conciliacao_municipio
// (5.580) são subconjuntos dela — verificado.
//
// LIMITAÇÃO: `municipio_norm` é o nome em caixa alta e sem acentos, e é a única
// forma do município disponível neste grão. Não há código IBGE de município nas
// tabelas publicadas, o que impede mapa por município e cruzamento com
// população do IBGE. É item do docs/ROTEIRO.md.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\combustivel_municipio.parquet")
    ),
    Colunas = Table.SelectColumns(
        Fonte,
        {"uf_sigla", "cod_uf_ibge", "regiao", "municipio_norm"}
    ),
    UfND = Table.ReplaceValue(Colunas, null, "ND", Replacer.ReplaceValue, {"uf_sigla"}),
    RegiaoND = Table.ReplaceValue(
        UfND, null, "Não disponível", Replacer.ReplaceValue, {"regiao"}
    ),
    Distintas = Table.Distinct(RegiaoND),
    ComChave = Table.AddColumn(
        Distintas,
        "chave_localidade",
        each [uf_sigla] & "|" & [municipio_norm],
        type text
    ),
    // Nome em caixa de título para exibição; a chave continua sendo o _norm.
    ComNome = Table.AddColumn(
        ComChave,
        "municipio",
        each Text.Proper([municipio_norm]),
        type text
    ),
    Tipos = Table.TransformColumnTypes(
        ComNome,
        {
            {"chave_localidade", type text},
            {"municipio", type text},
            {"municipio_norm", type text},
            {"uf_sigla", type text},
            {"cod_uf_ibge", Int64.Type},
            {"regiao", type text}
        }
    ),
    Ordem = Table.SelectColumns(
        Tipos,
        {"chave_localidade", "municipio", "municipio_norm", "uf_sigla", "cod_uf_ibge", "regiao"}
    )
in
    Ordem
