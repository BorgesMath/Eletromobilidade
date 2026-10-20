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
// `pbe_*` é o confronto com a tabela PBE Veicular do Inmetro, que traz a
// propulsão declarada pelo fabricante. `pbe_aviso` tem duas direções, e elas se
// leem de formas opostas:
//   - `sem_versao_no_pbe`: a regra disse eletrificado e o PBE não tem essa versão
//     para o modelo. Falso positivo provável — é a fila acionável.
//   - `pbe_so_eletrificado`: a regra disse combustão e toda versão do modelo no
//     PBE é eletrificada. Em geral é geração antiga, não regra faltando, porque o
//     PBE do ciclo só traz o que está em linha. Não trate como erro sem conferir
//     o ano de fabricação.
// `pbe_classes` vazio não é divergência: é moto, ônibus, caminhão ou modelo fora
// de linha, que o PBE não cobre.
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
            {"padrao", type text},
            {"marca", type text},
            {"pbe_classes", type text},
            {"pbe_categoria", type text},
            {"pbe_aviso", type text}
        }
    ),
    Final = Table.SelectColumns(
        Tipos,
        {"data_referencia", "marca_modelo_norm", "marca", "classe", "regra", "qtd_veiculos", "revisar",
         "padrao", "pbe_classes", "pbe_categoria", "pbe_aviso"}
    )
in
    Final
