"""Construção da base de eletromobilidade a partir dos arquivos de frota por combustível.

Produtos:

* ``frota_combustivel``: base tratada completa (todos os combustíveis), grão
  mês x município x rótulo de combustível. É o denominador das participações.
* ``eletromobilidade_longo``: recorte da base anterior com ``eletrificado == True``.
* ``eletromobilidade_{municipio,uf,brasil}``: painéis com a frota por classe,
  frota total, frota eletrificada e participação eletrificada.
* ``combustiveis_classificados``: auditoria dos rótulos encontrados e da classe
  atribuída a cada um.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .classificacao import CLASSES, CLASSES_ELETRIFICADAS, carregar_tabela, classificar
from .leitura import EXTENSOES_DADOS, inferir_periodo, ler_frota_combustivel
from .texto import normalizar
from .ufs import resolver_uf

log = logging.getLogger(__name__)

CHAVE_TEMPO = ["ano", "mes", "data_referencia"]
CHAVE_UF = ["uf_sigla", "cod_uf_ibge", "regiao"]


def processar_arquivo(caminho: str | Path, periodo: tuple[int, int] | None = None,
                      tabela: dict[str, str] | None = None) -> pd.DataFrame:
    """Lê, classifica e enriquece um arquivo mensal de frota por combustível."""
    caminho = Path(caminho)
    periodo = periodo or inferir_periodo(caminho)
    if periodo is None:
        raise ValueError(f"Período não identificado no nome de {caminho.name}; informe-o explicitamente.")
    ano, mes = periodo

    df = ler_frota_combustivel(caminho)
    ufs = df["uf"].map(resolver_uf)
    df["uf_sigla"] = ufs.map(lambda u: u[0] if u else None)
    df["cod_uf_ibge"] = ufs.map(lambda u: u[1] if u else None).astype("Int64")
    df["regiao"] = ufs.map(lambda u: u[2] if u else None)
    df["municipio_norm"] = df["municipio"].map(normalizar)
    df = df.join(classificar(df["combustivel"], tabela))
    df.insert(0, "data_referencia", pd.Timestamp(year=ano, month=mes, day=1))
    df.insert(0, "mes", mes)
    df.insert(0, "ano", ano)
    df["arquivo_origem"] = caminho.name

    sem_uf = df["uf_sigla"].isna()
    if sem_uf.any():
        log.info("%s: %d veículos sem UF válida (rótulos: %s).", caminho.name,
                 df.loc[sem_uf, "qtd_veiculos"].sum(), sorted(df.loc[sem_uf, "uf"].dropna().unique()))
    return df


def localizar_arquivos(pasta: str | Path) -> list[Path]:
    """Arquivos de frota por combustível sob ``pasta`` (busca recursiva pelo nome)."""
    return sorted(
        p for p in Path(pasta).rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSOES_DADOS and "COMBUSTIVEL" in normalizar(p.name)
    )


def processar_arquivos(caminhos: list[Path], tabela: dict[str, str] | None = None) -> pd.DataFrame:
    """Processa vários arquivos mensais; falha se dois arquivos cobrirem o mesmo mês."""
    if not caminhos:
        raise FileNotFoundError("Nenhum arquivo de frota por combustível para processar.")
    tabela = tabela or carregar_tabela()
    periodos: dict[tuple[int, int], Path] = {}
    partes = []
    for caminho in caminhos:
        periodo = inferir_periodo(caminho)
        if periodo in periodos:
            raise ValueError(f"Dois arquivos para {periodo[1]:02d}/{periodo[0]}: "
                             f"{periodos[periodo].name} e {caminho.name}")
        periodos[periodo] = caminho
        log.info("Processando %s", caminho.name)
        partes.append(processar_arquivo(caminho, periodo, tabela))
    return pd.concat(partes, ignore_index=True).sort_values(
        ["ano", "mes", "uf_sigla", "municipio_norm", "combustivel_norm"], na_position="last"
    ).reset_index(drop=True)


def _painel(longo: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    tabela = (longo.groupby(chave + ["classe"], dropna=False, observed=True)["qtd_veiculos"].sum()
              .unstack("classe", fill_value=0)
              .reindex(columns=list(CLASSES), fill_value=0)
              .astype("int64"))
    tabela.columns = [f"frota_{c}" for c in tabela.columns]
    tabela["frota_total"] = tabela.sum(axis=1)
    tabela["frota_eletrificada"] = tabela[[f"frota_{c}" for c in CLASSES_ELETRIFICADAS]].sum(axis=1)
    tabela["participacao_eletrificada"] = tabela["frota_eletrificada"] / tabela["frota_total"].where(
        tabela["frota_total"] > 0)
    return tabela.reset_index()


def painel_municipio(longo: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por mês x município. Municípios sem UF válida são mantidos com UF nula."""
    return _painel(longo, CHAVE_TEMPO + CHAVE_UF + ["municipio_norm"])


def painel_uf(longo: pd.DataFrame) -> pd.DataFrame:
    return _painel(longo.dropna(subset=["uf_sigla"]), CHAVE_TEMPO + CHAVE_UF)


def painel_brasil(longo: pd.DataFrame) -> pd.DataFrame:
    """Total nacional, incluindo registros sem UF válida."""
    return _painel(longo, CHAVE_TEMPO)


def auditoria_combustiveis(longo: pd.DataFrame) -> pd.DataFrame:
    return (longo.groupby(["combustivel", "combustivel_norm", "classe", "eletrificado", "origem_classificacao"],
                          dropna=False, observed=True)
            .agg(qtd_veiculos=("qtd_veiculos", "sum"),
                 primeiro_mes=("data_referencia", "min"), ultimo_mes=("data_referencia", "max"))
            .reset_index()
            .sort_values(["classe", "qtd_veiculos"], ascending=[True, False]))


def construir_base(longo: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "frota_combustivel": longo,
        "eletromobilidade_longo": longo[longo["eletrificado"]].reset_index(drop=True),
        "eletromobilidade_municipio": painel_municipio(longo),
        "eletromobilidade_uf": painel_uf(longo),
        "eletromobilidade_brasil": painel_brasil(longo),
        "combustiveis_classificados": auditoria_combustiveis(longo),
    }


def salvar(tabelas: dict[str, pd.DataFrame], destino: str | Path, csv: bool = True) -> list[Path]:
    """Grava cada tabela em Parquet e, opcionalmente, em CSV no padrão Excel pt-BR (``;`` e ``,``)."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    gravados = []
    for nome, df in tabelas.items():
        caminho = destino / f"{nome}.parquet"
        df.to_parquet(caminho, index=False)
        gravados.append(caminho)
        if csv:
            caminho = destino / f"{nome}.csv"
            df.to_csv(caminho, index=False, sep=";", decimal=",", encoding="utf-8-sig", date_format="%Y-%m-%d")
            gravados.append(caminho)
    return gravados
