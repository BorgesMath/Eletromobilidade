// fFrotaModelo — fato de detalhe por marca, modelo e ano de fabricação
//
// Fonte: resultados/modelo_eletrificados.parquet (195.356 linhas)
// Grão de saída: mês × município × marca_modelo × ano de fabricação × classe
//
// Só traz eletrificados e híbridos leves — a tabela publicada já é filtrada.
// Por isso NÃO se calcula participação com este fato: o denominador (frota
// total) não está aqui. Use fFrotaCombustivel para qualquer razão.
//
// Cobertura hoje: dez/2020 e set/2026 (dois meses). Ver docs/ROTEIRO.md.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\modelo_eletrificados.parquet")
    ),
    Tipos = Table.TransformColumnTypes(
        Fonte,
        {
            {"data_referencia", type date},
            {"uf_sigla", type text},
            {"municipio_norm", type text},
            {"cod_municipio_ibge", Int64.Type},
            {"marca_modelo", type text},
            {"ano_fabricacao", Int64.Type},
            {"classe", type text},
            {"qtd_veiculos", Int64.Type}
        }
    ),
    ComChave = Table.AddColumn(
        Tipos,
        "chave_localidade",
        each ChaveLocalidade([cod_municipio_ibge], [uf_sigla], [municipio_norm]),
        type text
    ),
    // marca_modelo é a chave de dModelo; o texto cru fica fora do fato.
    Final = Table.SelectColumns(
        ComChave,
        {
            "data_referencia",
            "chave_localidade",
            "marca_modelo",
            "ano_fabricacao",
            "classe",
            "qtd_veiculos"
        }
    )
in
    Final
