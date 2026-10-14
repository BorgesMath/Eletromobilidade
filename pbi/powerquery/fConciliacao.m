// fConciliacao — fato da página de auditoria
//
// Fonte: resultados/conciliacao_municipio.parquet (11.147 linhas)
// Grão de saída: mês × município
//
// Mantido LARGO de propósito. Cada métrica existe em quatro versões
// (_combustivel, _modelo, _diferenca, _razao) e o uso é comparar colunas lado a
// lado numa matriz, não cortar por uma dimensão de classe. Despivotar aqui só
// complicaria as medidas.
//
// Usa o grão de município (e não conciliacao_uf.csv) para relacionar com a
// mesma dLocalidade dos outros fatos. Agregar daqui para UF e Brasil reproduz
// exatamente conciliacao_uf.csv e conciliacao_brasil.csv.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\conciliacao_municipio.parquet")
    ),
    UfND = Table.ReplaceValue(Fonte, null, "ND", Replacer.ReplaceValue, {"uf_sigla"}),
    ComChave = Table.AddColumn(
        UfND,
        "chave_localidade",
        each [uf_sigla] & "|" & [municipio_norm],
        type text
    ),
    Tipos = Table.TransformColumnTypes(
        ComChave,
        {
            {"data_referencia", type date},
            {"chave_localidade", type text},
            {"total_combustivel", Int64.Type},
            {"total_modelo", Int64.Type},
            {"total_diferenca", Int64.Type},
            {"eletrico_combustivel", Int64.Type},
            {"eletrico_modelo", Int64.Type},
            {"eletrico_diferenca", Int64.Type},
            {"hibrido_plug_in_combustivel", Int64.Type},
            {"hibrido_plug_in_modelo", Int64.Type},
            {"hibrido_plug_in_diferenca", Int64.Type},
            {"hibrido_combustivel", Int64.Type},
            {"hibrido_modelo", Int64.Type},
            {"hibrido_diferenca", Int64.Type},
            {"hibridos_combustivel", Int64.Type},
            {"hibridos_modelo", Int64.Type},
            {"hibridos_diferenca", Int64.Type},
            {"eletrificada_combustivel", Int64.Type},
            {"eletrificada_modelo", Int64.Type},
            {"eletrificada_diferenca", Int64.Type},
            {"hibrido_leve_modelo", Int64.Type}
        }
    ),
    // As colunas *_razao são recalculadas em DAX a partir dos somatórios:
    // média de razão não é a razão das somas.
    Final = Table.RemoveColumns(
        Tipos,
        List.Select(Table.ColumnNames(Tipos), each Text.EndsWith(_, "_razao"))
            & {"ano", "mes", "uf_sigla", "cod_uf_ibge", "regiao", "municipio_norm"}
    )
in
    Final
