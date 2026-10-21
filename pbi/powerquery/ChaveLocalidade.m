// ChaveLocalidade — a chave de dLocalidade, a mesma nos quatro lugares que a usam
//
// Função, não tabela: dLocalidade, fFrotaCombustivel, fFrotaModelo e fConciliacao
// chamam esta consulta para montar chave_localidade. Escrever a fórmula quatro
// vezes é como dimensão e fato acabam divergindo.
//
// O município é o código IBGE de 7 dígitos, em texto. Os três pseudo-municípios
// da SENATRAN (SEM INFORMACAO, NAO IDENTIFICADO, NAO SE APLICA) não têm UF nem
// código; a chave deles é "ND|" seguido do nome. Um município com UF e sem código
// só aparece se o Python deixar resíduo, e aí o teste sobre resultados/ já falhou;
// a chave dele fica "UF|nome", para não colidir com outro de mesmo nome.

(cod_municipio_ibge as nullable number, uf_sigla as nullable text, municipio_norm as text) as text =>
    if cod_municipio_ibge <> null then
        Text.From(cod_municipio_ibge)
    else
        (if uf_sigla = null then "ND" else uf_sigla) & "|" & municipio_norm
