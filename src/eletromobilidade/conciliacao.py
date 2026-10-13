"""Conciliação entre a base por combustível e a base por modelo.

As duas bases vêm do mesmo cadastro (RENAVAM) no mesmo mês, por caminhos
diferentes: a primeira usa o campo combustível; a segunda infere a tecnologia
do nome do modelo. A comparação mede a qualidade da classificação por modelo
(e, onde a diferença se concentra, aponta regras faltando ou erradas).

Indicadores comparados (``<indicador>_combustivel``, ``<indicador>_modelo``,
``<indicador>_diferenca`` = modelo - combustível, ``<indicador>_razao`` = modelo / combustível):

* ``total``: frota total. Deve coincidir se os dois arquivos forem do mesmo recorte.
* ``eletrico``: tração 100% elétrica.
* ``hibrido_plug_in``: híbridos recarregáveis na tomada (PHEV).
* ``hibrido``: híbridos convencionais (HEV), cuja bateria só é recarregada pelo
  motor a combustão e pela frenagem regenerativa.
* ``hibridos``: soma dos dois anteriores. No campo combustível parte dos PHEV
  aparece como "GASOLINA/ELETRICO" (ver README), então a soma é mais comparável
  entre as bases do que cada parcela.
* ``eletrificada``: soma das classes eletrificadas.

``hibrido_leve_modelo`` é informado à parte: no campo combustível esses
veículos provavelmente aparecem como flex/gasolina.
"""

from __future__ import annotations

import pandas as pd

from .pipeline import CHAVE_MUNICIPIO, CHAVE_TEMPO, CHAVE_UF

INDICADORES = {
    "total": ["frota_total"],
    "eletrico": ["frota_eletrico"],
    "hibrido_plug_in": ["frota_hibrido_plug_in"],
    "hibrido": ["frota_hibrido"],
    "hibridos": ["frota_hibrido_plug_in", "frota_hibrido"],
    "eletrificada": ["frota_eletrificada"],
}


def conciliar(painel_combustivel: pd.DataFrame, painel_modelo: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    """Compara dois painéis de mesmo grão (``chave``). Junção externa: recortes de um lado só aparecem com nulos."""
    def indicadores(painel: pd.DataFrame, sufixo: str) -> pd.DataFrame:
        saida = painel[chave].copy()
        for nome, colunas in INDICADORES.items():
            saida[f"{nome}_{sufixo}"] = painel[colunas].sum(axis=1)
        return saida

    comb = indicadores(painel_combustivel, "combustivel")
    mod = indicadores(painel_modelo, "modelo")
    mod["hibrido_leve_modelo"] = painel_modelo["frota_hibrido_leve"]
    df = comb.merge(mod, on=chave, how="outer", validate="one_to_one")
    for nome in INDICADORES:
        c, m = df[f"{nome}_combustivel"], df[f"{nome}_modelo"]
        df[f"{nome}_diferenca"] = m - c
        df[f"{nome}_razao"] = m / c.where(c > 0)
    ordem = chave + [f"{n}_{s}" for n in INDICADORES for s in ("combustivel", "modelo", "diferenca", "razao")]
    return df[ordem + ["hibrido_leve_modelo"]].sort_values(chave, na_position="last").reset_index(drop=True)


def conciliar_bases(tabelas: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Conciliação nos três níveis, restrita aos meses presentes nas duas bases."""
    meses = (set(map(tuple, tabelas["combustivel_brasil"][["ano", "mes"]].values))
             & set(map(tuple, tabelas["modelo_brasil"][["ano", "mes"]].values)))
    if not meses:
        return {}

    def nos_meses(df: pd.DataFrame) -> pd.DataFrame:
        return df[[(a, m) in meses for a, m in zip(df["ano"], df["mes"])]]

    niveis = {"brasil": CHAVE_TEMPO, "uf": CHAVE_TEMPO + CHAVE_UF, "municipio": CHAVE_MUNICIPIO}
    return {
        f"conciliacao_{nivel}": conciliar(nos_meses(tabelas[f"combustivel_{nivel}"]),
                                          nos_meses(tabelas[f"modelo_{nivel}"]), chave)
        for nivel, chave in niveis.items()
    }
