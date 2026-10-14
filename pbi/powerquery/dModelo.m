// dModelo — dimensão de marca e modelo
//
// Fonte: resultados/modelo_eletrificados.parquet
// Grão: marca_modelo distinto (935 membros)
//
// O campo `Marca Modelo` do RENAVAM é um texto único, não dois campos. A marca
// é extraída daqui:
//   - prefixo `I/` indica veículo importado e é removido antes de ler a marca;
//   - havendo `/` no restante, a marca é o que vem antes (TOYOTA/COROLLA…);
//   - não havendo, é a primeira palavra (I/BYD DOLPHIN GS 180EV → BYD).
//
// LIMITAÇÃO: a marca sai como está no RENAVAM, que não é normalizado. Das 118
// marcas derivadas, algumas são a mesma empresa grafada de formas diferentes
// (CHEV e CHEVROLET; CAOACHERY e CHERY) e uma ou outra é modelo lido como marca
// (CIVIC). Para somar por fabricante, normalize antes — item do docs/ROTEIRO.md.
// Até lá, agregue por marca com ressalva e prefira o grão de modelo.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\modelo_eletrificados.parquet")
    ),
    Nomes = Table.Distinct(Table.SelectColumns(Fonte, {"marca_modelo"})),
    Importado = Table.AddColumn(
        Nomes, "importado", each Text.StartsWith([marca_modelo], "I/"), type logical
    ),
    SemPrefixo = Table.AddColumn(
        Importado,
        "sem_prefixo",
        each if [importado] then Text.RemoveRange([marca_modelo], 0, 2) else [marca_modelo],
        type text
    ),
    ComMarca = Table.AddColumn(
        SemPrefixo,
        "marca",
        each if Text.Contains([sem_prefixo], "/") then
            Text.BeforeDelimiter([sem_prefixo], "/")
        else
            Text.BeforeDelimiter([sem_prefixo], " "),
        type text
    ),
    ComOrigem = Table.AddColumn(
        ComMarca,
        "origem",
        each if [importado] then "Importado" else "Nacional",
        type text
    ),
    Final = Table.SelectColumns(ComOrigem, {"marca_modelo", "marca", "origem", "importado"})
in
    Final
