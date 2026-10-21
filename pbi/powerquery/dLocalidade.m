// dLocalidade — dimensão de município, UF e região (denormalizada)
//
// Fonte: resultados/municipios_dimensao.parquet
// Grão: município do IBGE (5.571) mais os 3 pseudo-municípios da SENATRAN —
// 5.574 membros
//
// Uma dimensão só, achatada, em vez de dMunicipio → dUF → dRegiao. Hierarquia
// natural, cardinalidade baixa, e evita snowflake sem ganho nenhum.
//
// A chave é o código IBGE (ver ChaveLocalidade), não o nome. A SENATRAN muda a
// grafia de alguns municípios no meio da série — EMBU vira EMBU DAS ARTES em
// abr/2022, GOUVEA vira GOUVEIA em mar/2024 —, e pelo nome cada grafia seria um
// membro, com a série cortada ao meio. Pelo código é um membro só. As grafias
// ficam em grafias_senatran, que é por onde se acha o município pelo nome antigo.
//
// O nome exibido é o oficial do IBGE, com acentos. Os pseudo-municípios não têm
// nome no IBGE e ficam com o da SENATRAN em caixa de título.
//
// cod_municipio_ibge é o campo de localização do mapa municipal (malha do IBGE,
// que identifica município pelo mesmo código) e a chave para cruzar com qualquer
// outra tabela do IBGE.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\municipios_dimensao.parquet")
    ),
    ComChave = Table.AddColumn(
        Fonte,
        "chave_localidade",
        each ChaveLocalidade([cod_municipio_ibge], [uf_sigla], [municipio_norm]),
        type text
    ),
    ComNome = Table.AddColumn(
        ComChave,
        "municipio",
        each if [municipio_ibge] <> null then [municipio_ibge] else Text.Proper([municipio_norm]),
        type text
    ),
    UfND = Table.ReplaceValue(ComNome, null, "ND", Replacer.ReplaceValue, {"uf_sigla"}),
    RegiaoND = Table.ReplaceValue(
        UfND, null, "Não disponível", Replacer.ReplaceValue, {"regiao"}
    ),
    Tipos = Table.TransformColumnTypes(
        RegiaoND,
        {
            {"chave_localidade", type text},
            {"cod_municipio_ibge", Int64.Type},
            {"municipio", type text},
            {"grafias_senatran", type text},
            {"uf_sigla", type text},
            {"cod_uf_ibge", Int64.Type},
            {"regiao", type text}
        }
    ),
    Ordem = Table.SelectColumns(
        Tipos,
        {"chave_localidade", "cod_municipio_ibge", "municipio", "grafias_senatran", "uf_sigla", "cod_uf_ibge", "regiao"}
    )
in
    Ordem
