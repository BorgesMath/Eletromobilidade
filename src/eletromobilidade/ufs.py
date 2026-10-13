"""Tabela de Unidades da Federação.

A SENATRAN identifica a UF pelo nome por extenso em caixa alta (``"SAO PAULO"``);
aqui ela é ligada à sigla, ao código IBGE da UF e à grande região.
"""

from __future__ import annotations

from .texto import normalizar

# nome normalizado: (sigla, código IBGE, região)
UFS: dict[str, tuple[str, int, str]] = {
    "RONDONIA": ("RO", 11, "Norte"),
    "ACRE": ("AC", 12, "Norte"),
    "AMAZONAS": ("AM", 13, "Norte"),
    "RORAIMA": ("RR", 14, "Norte"),
    "PARA": ("PA", 15, "Norte"),
    "AMAPA": ("AP", 16, "Norte"),
    "TOCANTINS": ("TO", 17, "Norte"),
    "MARANHAO": ("MA", 21, "Nordeste"),
    "PIAUI": ("PI", 22, "Nordeste"),
    "CEARA": ("CE", 23, "Nordeste"),
    "RIO GRANDE DO NORTE": ("RN", 24, "Nordeste"),
    "PARAIBA": ("PB", 25, "Nordeste"),
    "PERNAMBUCO": ("PE", 26, "Nordeste"),
    "ALAGOAS": ("AL", 27, "Nordeste"),
    "SERGIPE": ("SE", 28, "Nordeste"),
    "BAHIA": ("BA", 29, "Nordeste"),
    "MINAS GERAIS": ("MG", 31, "Sudeste"),
    "ESPIRITO SANTO": ("ES", 32, "Sudeste"),
    "RIO DE JANEIRO": ("RJ", 33, "Sudeste"),
    "SAO PAULO": ("SP", 35, "Sudeste"),
    "PARANA": ("PR", 41, "Sul"),
    "SANTA CATARINA": ("SC", 42, "Sul"),
    "RIO GRANDE DO SUL": ("RS", 43, "Sul"),
    "MATO GROSSO DO SUL": ("MS", 50, "Centro-Oeste"),
    "MATO GROSSO": ("MT", 51, "Centro-Oeste"),
    "GOIAS": ("GO", 52, "Centro-Oeste"),
    "DISTRITO FEDERAL": ("DF", 53, "Centro-Oeste"),
}

_POR_SIGLA = {sigla: nome for nome, (sigla, _, _) in UFS.items()}


def resolver_uf(valor: object) -> tuple[str, int, str] | None:
    """Aceita nome por extenso ou sigla; devolve ``(sigla, cod_ibge, regiao)`` ou ``None``.

    ``None`` indica registros sem UF válida (ex.: ``"Sem Informação"``).
    """
    chave = normalizar(valor)
    if chave in UFS:
        return UFS[chave]
    if chave in _POR_SIGLA:
        return UFS[_POR_SIGLA[chave]]
    return None
