"""Construção das bases de eletromobilidade.

Duas bases independentes, combináveis pela conciliação (``conciliacao.py``):

* **por combustível** (``frota_combustivel``): o combustível vem do RENAVAM.
  Produtos ``frota_combustivel``, ``combustivel_eletrificados``,
  ``combustivel_{municipio,uf,brasil}`` e ``combustiveis_classificados``.
* **por modelo** (``base_modelo.py``): a tecnologia é inferida do nome do
  modelo. Produtos ``modelo_eletrificados``, ``modelo_{municipio,uf,brasil}`` e
  ``modelos_classificados``.

Os painéis têm uma linha por mês x recorte geográfico, com a frota de cada
classe (``frota_<classe>``), ``frota_total``, ``frota_eletrificada`` e
``participacao_eletrificada``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .classificacao import CLASSES, CLASSES_ELETRIFICADAS, carregar_tabela, classificar
from .leitura import EXTENSOES_DADOS, identificar_tabela, inferir_periodo, ler_frota_combustivel
from .texto import normalizar
from .ufs import resolver_uf

log = logging.getLogger(__name__)

CHAVE_TEMPO = ["ano", "mes", "data_referencia"]
CHAVE_UF = ["uf_sigla", "cod_uf_ibge", "regiao"]
CHAVE_MUNICIPIO = CHAVE_TEMPO + CHAVE_UF + ["municipio_norm"]


# --- utilidades comuns às duas bases ----------------------------------------------------

def localizar_arquivos(pasta: str | Path, tabela: str) -> list[Path]:
    """Arquivos da ``tabela`` (``"combustivel"``, ``"marca_modelo"``...) sob ``pasta``, pelo nome."""
    return sorted(
        p for p in Path(pasta).rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSOES_DADOS and identificar_tabela(p.name) == tabela
    )


def periodos_por_arquivo(caminhos: list[Path]) -> dict[Path, tuple[int, int]]:
    """Período de cada arquivo; falha se não identificado ou se dois arquivos cobrirem o mesmo mês."""
    vistos: dict[tuple[int, int], Path] = {}
    for caminho in caminhos:
        periodo = inferir_periodo(caminho)
        if periodo is None:
            raise ValueError(f"Período não identificado no nome de {caminho.name}.")
        if periodo in vistos:
            raise ValueError(f"Dois arquivos para {periodo[1]:02d}/{periodo[0]}: "
                             f"{vistos[periodo].name} e {caminho.name}")
        vistos[periodo] = caminho
    return {c: p for p, c in vistos.items()}


def enriquecer(df: pd.DataFrame, periodo: tuple[int, int], arquivo: str | None = None) -> pd.DataFrame:
    """Acrescenta período, sigla/código/região da UF e município normalizado."""
    ano, mes = periodo
    ufs = df["uf"].map(resolver_uf)
    df = df.assign(
        uf_sigla=ufs.map(lambda u: u[0] if u else None),
        cod_uf_ibge=ufs.map(lambda u: u[1] if u else None).astype("Int64"),
        regiao=ufs.map(lambda u: u[2] if u else None),
        municipio_norm=df["municipio"].map(normalizar),
    )
    df.insert(0, "data_referencia", pd.Timestamp(year=ano, month=mes, day=1))
    df.insert(0, "mes", mes)
    df.insert(0, "ano", ano)
    if arquivo is not None:
        df["arquivo_origem"] = arquivo
    sem_uf = df["uf_sigla"].isna()
    if sem_uf.any():
        log.info("%s: %d veículos sem UF válida (rótulos: %s).", arquivo or periodo,
                 df.loc[sem_uf, "qtd_veiculos"].sum(), sorted(df.loc[sem_uf, "uf"].dropna().unique()))
    return df


def painel(longo: pd.DataFrame, chave: list[str], classes: tuple[str, ...],
           eletrificadas: tuple[str, ...]) -> pd.DataFrame:
    """Frota por classe em colunas, com total, eletrificada e participação."""
    tabela = (longo.groupby(chave + ["classe"], dropna=False, observed=True)["qtd_veiculos"].sum()
              .unstack("classe", fill_value=0)
              .reindex(columns=list(classes), fill_value=0)
              .astype("int64"))
    tabela.columns = [f"frota_{c}" for c in tabela.columns]
    tabela["frota_total"] = tabela.sum(axis=1)
    tabela["frota_eletrificada"] = tabela[[f"frota_{c}" for c in eletrificadas]].sum(axis=1)
    tabela["participacao_eletrificada"] = tabela["frota_eletrificada"] / tabela["frota_total"].where(
        tabela["frota_total"] > 0)
    return tabela.reset_index()


def paineis(longo: pd.DataFrame, prefixo: str, classes: tuple[str, ...],
            eletrificadas: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    """Painéis por município (UF nula quando inválida), UF (só válidas) e Brasil (tudo)."""
    return {
        f"{prefixo}_municipio": painel(longo, CHAVE_MUNICIPIO, classes, eletrificadas),
        f"{prefixo}_uf": painel(longo.dropna(subset=["uf_sigla"]), CHAVE_TEMPO + CHAVE_UF, classes, eletrificadas),
        f"{prefixo}_brasil": painel(longo, CHAVE_TEMPO, classes, eletrificadas),
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


# --- base por combustível ---------------------------------------------------------------

def processar_arquivo(caminho: str | Path, periodo: tuple[int, int] | None = None,
                      tabela: dict[str, str] | None = None) -> pd.DataFrame:
    """Lê, classifica e enriquece um arquivo mensal de frota por combustível."""
    caminho = Path(caminho)
    periodo = periodo or inferir_periodo(caminho)
    if periodo is None:
        raise ValueError(f"Período não identificado no nome de {caminho.name}; informe-o explicitamente.")
    df = ler_frota_combustivel(caminho)
    df = enriquecer(df, periodo, caminho.name)
    return df.join(classificar(df["combustivel"], tabela))


def processar_arquivos(caminhos: list[Path], tabela: dict[str, str] | None = None) -> pd.DataFrame:
    """Processa vários arquivos mensais por combustível; falha se dois cobrirem o mesmo mês."""
    if not caminhos:
        raise FileNotFoundError("Nenhum arquivo de frota por combustível para processar.")
    tabela = tabela or carregar_tabela()
    partes = []
    for caminho, periodo in periodos_por_arquivo(caminhos).items():
        log.info("Processando %s", caminho.name)
        partes.append(processar_arquivo(caminho, periodo, tabela))
    return pd.concat(partes, ignore_index=True).sort_values(
        ["ano", "mes", "uf_sigla", "municipio_norm", "combustivel_norm"], na_position="last"
    ).reset_index(drop=True)


def auditoria_combustiveis(longo: pd.DataFrame) -> pd.DataFrame:
    return (longo.groupby(["combustivel", "combustivel_norm", "classe", "eletrificado", "origem_classificacao"],
                          dropna=False, observed=True)
            .agg(qtd_veiculos=("qtd_veiculos", "sum"),
                 primeiro_mes=("data_referencia", "min"), ultimo_mes=("data_referencia", "max"))
            .reset_index()
            .sort_values(["classe", "qtd_veiculos"], ascending=[True, False]))


def construir_base_combustivel(longo: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "frota_combustivel": longo,
        "combustivel_eletrificados": longo[longo["eletrificado"]].reset_index(drop=True),
        **paineis(longo, "combustivel", CLASSES, CLASSES_ELETRIFICADAS),
        "combustiveis_classificados": auditoria_combustiveis(longo),
    }
