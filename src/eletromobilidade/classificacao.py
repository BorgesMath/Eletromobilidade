"""Classificação dos rótulos de combustível do RENAVAM em classes de eletromobilidade.

A fonte primária é a tabela ``dados/combustiveis.csv`` (auditável e editável).
Rótulos ausentes da tabela caem em regras textuais e são marcados com
``origem_classificacao == "regra"``, para que possam ser revisados e incorporados
à tabela.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .texto import normalizar_combustivel

CLASSES = ("eletrico", "hibrido_plug_in", "hibrido", "celula_combustivel", "combustao", "sem_informacao")
CLASSES_ELETRIFICADAS = ("eletrico", "hibrido_plug_in", "hibrido", "celula_combustivel")

TABELA_PADRAO = Path(__file__).parent / "dados" / "combustiveis.csv"

# Termos que indicam motor de combustão interna num rótulo que também cita "ELETRICO".
_TERMICOS = ("GASOL", "ALCOOL", "ETANOL", "DIESEL", "GAS ", "GAS/", "GNV", "METANO", "FLEX")

_SEM_INFORMACAO = ("SEM INFORMACAO", "NAO IDENTIFICADO", "NAO SE APLICA", "VIDE/CAMPO/OBSERVACAO")


def carregar_tabela(caminho: str | Path | None = None) -> dict[str, str]:
    """Lê a tabela combustível -> classe. Sem argumento, usa a tabela embutida no pacote."""
    caminho = Path(caminho) if caminho is not None else TABELA_PADRAO
    tabela = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8")
    invalidas = set(tabela["classe"]) - set(CLASSES)
    if invalidas:
        raise ValueError(f"Classes desconhecidas em {caminho}: {sorted(invalidas)}")
    return {normalizar_combustivel(c): k for c, k in zip(tabela["combustivel"], tabela["classe"])}


def classificar_por_regra(combustivel_norm: str) -> str:
    """Classe inferida de um rótulo já normalizado que não consta da tabela."""
    c = combustivel_norm
    if not c or c in _SEM_INFORMACAO:
        return "sem_informacao"
    if "PLUG-IN" in c:
        return "hibrido_plug_in"
    if "CELULA" in c or "HIDROGENIO" in c:
        return "celula_combustivel"
    if "ELETRIC" in c:
        return "hibrido" if any(t in c for t in _TERMICOS) else "eletrico"
    return "combustao"


def classificar(combustiveis: pd.Series, tabela: dict[str, str] | None = None) -> pd.DataFrame:
    """Classifica uma série de rótulos brutos.

    Retorna um DataFrame alinhado ao índice de entrada com as colunas
    ``combustivel_norm``, ``classe``, ``eletrificado`` e ``origem_classificacao``.
    """
    if tabela is None:
        tabela = carregar_tabela()
    unicos = pd.Series(combustiveis.unique())
    norm = unicos.map(normalizar_combustivel)
    na_tabela = norm.isin(tabela.keys())
    classe = norm.map(tabela).where(na_tabela, norm.map(classificar_por_regra))
    mapa = pd.DataFrame(
        {
            "combustivel_norm": norm.values,
            "classe": classe.values,
            "origem_classificacao": na_tabela.map({True: "tabela", False: "regra"}).values,
        },
        index=unicos.values,
    )
    resultado = mapa.reindex(combustiveis.values)
    resultado.index = combustiveis.index
    resultado["eletrificado"] = resultado["classe"].isin(CLASSES_ELETRIFICADAS)
    return resultado[["combustivel_norm", "classe", "eletrificado", "origem_classificacao"]]
