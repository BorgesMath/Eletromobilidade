// dClasse — dimensão de classe de tecnologia
//
// Tabela fixa, digitada aqui. É pequena, estável e carrega as decisões
// metodológicas do painel: quem entra na frota eletrificada e em que ordem as
// classes aparecem nos visuais.
//
// Espelha as classes de resultados/DICIONARIO.md. Se as regras de
// src/eletromobilidade/dados/ mudarem as classes, atualize esta tabela.
//
// `eletrificado` reproduz a definição do pacote: elétrico, híbrido plug-in,
// híbrido convencional e célula de combustível. Híbrido leve fica FORA — o
// motor elétrico não traciona sozinho.
//
// `ordem` serve para Classificar por coluna em `rotulo` (do mais ao menos
// elétrico), senão o Power BI ordena em ordem alfabética.

let
    Fonte = Table.FromRows(
        {
            {"eletrico", "Elétrico (BEV)", true, 1, "Eletrificado"},
            {"hibrido_plug_in", "Híbrido plug-in (PHEV)", true, 2, "Eletrificado"},
            {"hibrido", "Híbrido (HEV)", true, 3, "Eletrificado"},
            {"celula_combustivel", "Célula de combustível (FCEV)", true, 4, "Eletrificado"},
            {"hibrido_leve", "Híbrido leve (MHEV)", false, 5, "Não eletrificado"},
            {"combustao", "Combustão", false, 6, "Não eletrificado"},
            {"nao_motorizado", "Não motorizado", false, 7, "Não eletrificado"},
            {"sem_informacao", "Sem informação", false, 8, "Sem informação"}
        },
        type table [
            classe = text,
            rotulo = text,
            eletrificado = logical,
            ordem = Int64.Type,
            grupo = text
        ]
    )
in
    Fonte
