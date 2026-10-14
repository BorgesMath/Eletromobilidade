// fCobertura — um registro por arquivo mensal da SENATRAN
//
// Fonte: resultados/qualidade_combustivel.csv (76 linhas) + qualidade_modelo.csv
// Grão: base × mês
//
// Alimenta a página de cobertura: quais meses existem, quantas linhas vieram de
// cada arquivo, que ajuste foi aplicado e se o mês entrou na série. É o que
// permite distinguir "frota zero" de "mês sem arquivo" nos visuais.
//
// Único CSV lido pelo modelo (os outros têm Parquet equivalente). Os CSVs do
// pacote são UTF-8 COM BOM, `;` como separador e `,` decimal — o BOM é removido
// à mão porque senão contamina o nome da primeira coluna.

let
    Ler = (arquivo as text, base as text) as table =>
        let
            Texto = Text.FromBinary(File.Contents(PastaResultados & "\" & arquivo), 65001),
            SemBOM = if Text.StartsWith(Texto, "#(feff)") then
                Text.RemoveRange(Texto, 0, 1)
            else
                Texto,
            Csv = Csv.Document(SemBOM, [Delimiter = ";", QuoteStyle = QuoteStyle.None]),
            Cabecalho = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
            Tipos = Table.TransformColumnTypes(
                Cabecalho,
                {
                    {"data_referencia", type date},
                    {"arquivo", type text},
                    {"linhas", Int64.Type},
                    {"frota_total", Int64.Type},
                    {"ajuste", type text},
                    {"incluido", type logical}
                },
                "pt-BR"
            ),
            ComBase = Table.AddColumn(Tipos, "base", each base, type text),
            Enxuta = Table.SelectColumns(
                ComBase,
                {"base", "data_referencia", "arquivo", "linhas", "frota_total", "ajuste", "incluido"}
            )
        in
            Enxuta,
    Combinada = Table.Combine(
        {
            Ler("qualidade_combustivel.csv", "Combustível"),
            Ler("qualidade_modelo.csv", "Modelo")
        }
    ),
    // Texto vazio em `ajuste` vira nulo para o visual não mostrar célula em branco falsa.
    SemVazio = Table.ReplaceValue(Combinada, "", null, Replacer.ReplaceValue, {"ajuste"}),
    ComFlag = Table.AddColumn(
        SemVazio, "tem_ajuste", each [ajuste] <> null, type logical
    )
in
    ComFlag
