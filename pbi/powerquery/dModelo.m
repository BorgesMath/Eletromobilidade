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
//
// O tipo de veículo (`tipo`: leve, moto, onibus, caminhao, outros) também chega
// pronto, de src/eletromobilidade/tipos.py: pelo PBE Veicular do Inmetro para
// quem está nele, por regra revisada para o resto. Aqui só se acrescentam o
// rótulo e a ordem de exibição, fixa — leve primeiro, por ser a maior parte.
// Modelo sem tipo (nome que nenhuma fonte identifica) aparece como
// "Sem tipo", e não some do total.

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
            {"origem", type text},
            {"tipo", type text},
            {"origem_tipo", type text}
        }
    ),
    Rotulos = [
        leve = {"Automóvel e comercial leve", 1},
        moto = {"Moto, scooter e ciclomotor", 2},
        onibus = {"Ônibus", 3},
        caminhao = {"Caminhão", 4},
        outros = {"Outros", 5}
    ],
    ComRotulo = Table.AddColumn(
        Tipos,
        "tipo_rotulo",
        each if [tipo] = null then "Sem tipo" else Record.Field(Rotulos, [tipo]){0},
        type text
    ),
    ComOrdem = Table.AddColumn(
        ComRotulo,
        "tipo_ordem",
        each if [tipo] = null then 9 else Record.Field(Rotulos, [tipo]){1},
        Int64.Type
    ),
    Final = Table.SelectColumns(
        ComOrdem,
        {"marca_modelo", "marca_renavam", "marca", "origem", "importado", "tipo", "tipo_rotulo", "tipo_ordem",
         "origem_tipo"}
    )
in
    Final
