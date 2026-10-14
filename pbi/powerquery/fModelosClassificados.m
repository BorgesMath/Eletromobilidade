// fModelosClassificados — auditoria da classificação por nome de modelo
//
// Fonte: resultados/modelos_classificados.parquet (70.869 linhas)
// Grão de saída: mês × modelo normalizado
//
// Uma linha por modelo por mês, com a classe atribuída, o número e o padrão da
// regra que a definiu, e a marcação `revisar`. É a fila de trabalho das regras
// de src/eletromobilidade/dados/modelos.csv: `revisar` = TRUE é modelo de marca
// que tem linha eletrificada mas que nenhuma regra alcançou.
//
// Não se relaciona com dLocalidade — a tabela publicada já é agregada no
// Brasil. Nos visuais, combine com dCalendario e dClasse apenas.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\modelos_classificados.parquet")
    ),
    Tipos = Table.TransformColumnTypes(
        Fonte,
        {
            {"data_referencia", type date},
            {"marca_modelo_norm", type text},
            {"classe", type text},
            {"regra", Int64.Type},
            {"qtd_veiculos", Int64.Type},
            {"revisar", type logical},
            {"padrao", type text}
        }
    ),
    Final = Table.SelectColumns(
        Tipos,
        {"data_referencia", "marca_modelo_norm", "classe", "regra", "qtd_veiculos", "revisar", "padrao"}
    )
in
    Final
