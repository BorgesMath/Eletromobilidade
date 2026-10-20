// dModelo — dimensão de marca e modelo
//
// Fonte: resultados/modelos_dimensao.parquet
// Grão: marca_modelo distinto (935 membros)
//
// A marca NÃO é derivada aqui. O campo `Marca Modelo` do RENAVAM é um texto
// único, e extrair a marca dele tem exceção suficiente para pedir teste: o
// primeiro elemento pode ser marcador de importação (`I/`, `IMP/`), a montadora
// que montou o veículo no Brasil (`JTA/SUZUKI EN125 YES`) ou o tipo do veículo,
// em reboque e máquina (`SR/RANDON SR CA`, `M.A./MASSEY-FERGUSON`). Isso mora em
// src/eletromobilidade/modelos.py e chega pronto nesta tabela.
//
// Duas colunas de marca, de propósito:
//   - `marca_renavam`: a grafia como o RENAVAM publica, para auditar;
//   - `marca`: a forma canônica, que une as grafias da mesma empresa por
//     src/eletromobilidade/dados/marcas.csv (GM, CHEVROLET e CHEV viram
//     CHEVROLET; CAOACHERY vira CHERY). Use esta para agregar por fabricante.
//
// LIMITAÇÃO: a tabela de equivalência cobre as grafias conferidas à mão. Grafia
// fora dela segue como está em `marca` — não há invenção, mas pode haver empresa
// ainda dividida em duas linhas. A fila do que falta sai no log de `processar`
// (grafias que parecem variante de outra) e em docs/ROTEIRO.md.

let
    Fonte = Parquet.Document(
        File.Contents(PastaResultados & "\modelos_dimensao.parquet")
    ),
    Tipos = Table.TransformColumnTypes(
        Fonte,
        {
            {"marca_modelo", type text},
            {"marca_modelo_norm", type text},
            {"marca_renavam", type text},
            {"marca", type text},
            {"importado", type logical},
            {"origem", type text}
        }
    ),
    Final = Table.SelectColumns(
        Tipos,
        {"marca_modelo", "marca_renavam", "marca", "origem", "importado"}
    )
in
    Final
