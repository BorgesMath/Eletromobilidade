"""Código IBGE e nome oficial do município.

A SENATRAN identifica o município só pelo nome, em caixa alta e sem acento, e o nome
não é estável: alguns municípios mudam de grafia no meio da série (``EMBU`` vira
``EMBU DAS ARTES`` em abr/2022, ``GOUVEA`` vira ``GOUVEIA`` em mar/2024). Pelo nome,
cada grafia seria um município diferente e a série dele quebraria no meio. O código
IBGE de 7 dígitos é a identidade estável, e é ele que liga a base a qualquer outra
tabela do IBGE (população, malha municipal).

Duas tabelas em ``dados/``:

* ``municipios.csv`` — instantâneo da lista oficial de municípios da API de
  localidades do IBGE (comando ``municipios``). Não se edita à mão.
* ``municipios_grafias.csv`` — as grafias da SENATRAN que não casam com o nome do
  IBGE, conferidas uma a uma, com o código e a razão: grafia antiga que a SENATRAN
  nunca atualizou (``PARATI``), nome anterior ao atual (``BOA SAUDE``, hoje Januário
  Cicco), erro de digitação (``BARAO D0 MONTE ALTO``) e distrito publicado como se
  fosse município (``IBITIUVA``, de Pitangueiras).

O casamento é por UF e nome sem acento e sem pontuação (hífen e apóstrofo viram
espaço), primeiro pela tabela de grafias, depois pelo nome do IBGE. Não há casamento
aproximado: grafia que não está em nenhuma das duas fica sem código, ``processar``
lista e o teste sobre ``resultados/`` falha. Só os três pseudo-municípios da
SENATRAN, que não têm UF, ficam sem código por construção.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .texto import normalizar
from .ufs import UFS

log = logging.getLogger(__name__)

URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
MUNICIPIOS_PADRAO = Path(__file__).parent / "dados" / "municipios.csv"
GRAFIAS_PADRAO = Path(__file__).parent / "dados" / "municipios_grafias.csv"

# Abaixo disto, a resposta da API não é a lista completa (o Brasil tem 5.571 municípios).
MINIMO_MUNICIPIOS = 5500

_COD_UF = {sigla: cod for sigla, cod, _ in UFS.values()}
_NAO_ALFANUMERICO = re.compile(r"[^A-Z0-9]+")


def chave_municipio(nome: object) -> str:
    """Nome para casamento: sem acento, caixa alta, pontuação vira espaço.

    ``"Pingo-d'Água"`` e ``"PINGO D'AGUA"`` dão ``"PINGO D AGUA"``.
    """
    return _NAO_ALFANUMERICO.sub(" ", normalizar(nome)).strip()


def _validar_codigos(tabela: pd.DataFrame, origem: str) -> None:
    """Código de 7 dígitos cujos 2 primeiros são o código da UF informada."""
    uf_do_codigo = tabela["cod_municipio_ibge"] // 100_000
    erradas = tabela[uf_do_codigo != tabela["uf_sigla"].map(_COD_UF)]
    if len(erradas):
        raise ValueError(f"{origem}: código IBGE incompatível com a UF em "
                         f"{erradas[['uf_sigla', 'cod_municipio_ibge']].values.tolist()[:5]}")


# --- instantâneo do IBGE ------------------------------------------------------------------

def tabela_ibge(registros: list[dict]) -> pd.DataFrame:
    """Converte a resposta da API de localidades (``view=nivelado``) na tabela do pacote."""
    tabela = pd.DataFrame({
        "cod_municipio_ibge": [int(r["municipio-id"]) for r in registros],
        "uf_sigla": [r["UF-sigla"] for r in registros],
        "municipio_ibge": [r["municipio-nome"] for r in registros],
    })
    if len(tabela) < MINIMO_MUNICIPIOS:
        raise ValueError(f"A API do IBGE devolveu {len(tabela)} municípios; esperados mais de {MINIMO_MUNICIPIOS}.")
    return tabela.sort_values("cod_municipio_ibge").reset_index(drop=True)


def baixar_municipios_ibge(sessao=None) -> pd.DataFrame:
    """Lista oficial de municípios, da API de localidades do IBGE."""
    from .coleta import criar_sessao

    sessao = sessao or criar_sessao()
    resposta = sessao.get(URL_IBGE, timeout=120)
    resposta.raise_for_status()
    return tabela_ibge(resposta.json())


def gravar_municipios(tabela: pd.DataFrame, caminho: str | Path | None = None) -> Path:
    caminho = Path(caminho) if caminho is not None else MUNICIPIOS_PADRAO
    tabela.to_csv(caminho, sep=";", index=False, encoding="utf-8")
    return caminho


def carregar_municipios(caminho: str | Path | None = None) -> pd.DataFrame:
    """Lê o instantâneo do IBGE. Valida código único, código coerente com a UF e
    nome único dentro da UF depois da normalização (senão o casamento seria ambíguo)."""
    caminho = Path(caminho) if caminho is not None else MUNICIPIOS_PADRAO
    tabela = pd.read_csv(caminho, sep=";", dtype={"cod_municipio_ibge": int}, keep_default_na=False,
                         encoding="utf-8")
    if tabela["cod_municipio_ibge"].duplicated().any():
        raise ValueError(f"Código IBGE repetido em {caminho.name}.")
    _validar_codigos(tabela, caminho.name)
    chaves = tabela["uf_sigla"] + "|" + tabela["municipio_ibge"].map(chave_municipio)
    if chaves.duplicated().any():
        raise ValueError(f"Nomes que a normalização torna iguais na mesma UF em {caminho.name}: "
                         f"{sorted(chaves[chaves.duplicated()])}")
    return tabela


def carregar_grafias(caminho: str | Path | None = None,
                     municipios: pd.DataFrame | None = None) -> pd.DataFrame:
    """Lê a tabela de grafias da SENATRAN, conferindo-a contra o instantâneo do IBGE.

    Falha se uma grafia aparece duas vezes, se o código não existe no IBGE ou é de
    outra UF, ou se a grafia já casa sozinha com o nome do IBGE — nesse caso a linha é
    redundante, ou contradiz o IBGE se apontar para outro código.
    """
    caminho = Path(caminho) if caminho is not None else GRAFIAS_PADRAO
    municipios = carregar_municipios() if municipios is None else municipios
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if linha.strip() and linha.count(";") != 3:
            raise ValueError(f"{caminho.name}, linha {numero}: esperados 4 campos separados por ';' "
                             f"(não use ';' dentro da nota): {linha[:80]}")
    tabela = pd.read_csv(caminho, sep=";", dtype={"cod_municipio_ibge": int}, keep_default_na=False,
                         encoding="utf-8")
    chaves = tabela["uf_sigla"] + "|" + tabela["municipio_senatran"].map(chave_municipio)
    if chaves.duplicated().any():
        raise ValueError(f"Grafias repetidas em {caminho.name}: {sorted(chaves[chaves.duplicated()])}")
    desconhecidos = set(tabela["cod_municipio_ibge"]) - set(municipios["cod_municipio_ibge"])
    if desconhecidos:
        raise ValueError(f"Códigos que não estão no IBGE em {caminho.name}: {sorted(desconhecidos)}")
    _validar_codigos(tabela, caminho.name)
    do_ibge = set(municipios["uf_sigla"] + "|" + municipios["municipio_ibge"].map(chave_municipio))
    redundantes = sorted(set(chaves) & do_ibge)
    if redundantes:
        raise ValueError(f"Grafias que já casam com o nome do IBGE em {caminho.name}: {redundantes}")
    return tabela


@lru_cache(maxsize=1)
def _codigos_padrao() -> dict[tuple[str, str], int]:
    return tabela_de_codigos()


def tabela_de_codigos(municipios: pd.DataFrame | None = None,
                      grafias: pd.DataFrame | None = None) -> dict[tuple[str, str], int]:
    """``(uf_sigla, chave do nome) -> código IBGE``, com o IBGE e as grafias da SENATRAN."""
    municipios = carregar_municipios() if municipios is None else municipios
    grafias = carregar_grafias(municipios=municipios) if grafias is None else grafias
    codigos = {(uf, chave_municipio(nome)): cod for uf, nome, cod in
               zip(municipios["uf_sigla"], municipios["municipio_ibge"], municipios["cod_municipio_ibge"])}
    codigos |= {(uf, chave_municipio(nome)): cod for uf, nome, cod in
                zip(grafias["uf_sigla"], grafias["municipio_senatran"], grafias["cod_municipio_ibge"])}
    return codigos


def codigos_municipio(uf_sigla: pd.Series, municipio: pd.Series,
                      codigos: dict[tuple[str, str], int] | None = None) -> pd.Series:
    """Código IBGE de cada registro; nulo sem UF válida ou sem casamento.

    O casamento é feito uma vez por par (UF, município) distinto, não por linha.
    """
    codigos = _codigos_padrao() if codigos is None else codigos
    pares = list(zip(uf_sigla, municipio))
    por_par = {par: codigos.get((par[0], chave_municipio(par[1]))) if isinstance(par[0], str) else None
               for par in set(pares)}
    return pd.Series([por_par[par] for par in pares], index=uf_sigla.index, dtype="Int64")


# --- dimensão e auditoria -----------------------------------------------------------------

_CHAVE_GRAFIA = ["uf_sigla", "cod_uf_ibge", "regiao", "cod_municipio_ibge", "municipio_norm"]


def sem_codigo(painel_municipio: pd.DataFrame) -> pd.DataFrame:
    """Municípios com UF válida e sem código IBGE: a fila de ``dados/municipios_grafias.csv``."""
    faltando = painel_municipio[painel_municipio["uf_sigla"].notna() & painel_municipio["cod_municipio_ibge"].isna()]
    return (faltando.groupby(["uf_sigla", "municipio_norm"])
            .agg(meses=("data_referencia", "nunique"), ultimo_mes=("data_referencia", "max"),
                 frota_total=("frota_total", "max"))
            .reset_index().sort_values("frota_total", ascending=False))


def dimensao_municipio(paineis: list[pd.DataFrame], municipios: pd.DataFrame | None = None) -> pd.DataFrame:
    """Dimensão de município a partir dos painéis municipais das bases: uma linha por código IBGE.

    Um município que a SENATRAN publicou com mais de uma grafia é uma linha só, com
    as grafias em ``grafias_senatran`` (ordem de aparição na série) e a mais recente
    em ``municipio_norm``. Os registros sem código (os pseudo-municípios sem UF) são
    uma linha por grafia, com ``cod_municipio_ibge`` e ``municipio_ibge`` nulos.
    """
    municipios = carregar_municipios() if municipios is None else municipios
    grafias = (pd.concat([p[_CHAVE_GRAFIA + ["data_referencia"]] for p in paineis], ignore_index=True)
               .groupby(_CHAVE_GRAFIA, dropna=False)["data_referencia"].agg(["min", "max"])
               .reset_index().sort_values(["min", "max", "municipio_norm"]))
    identidade = grafias["cod_municipio_ibge"].astype("string").fillna(
        grafias["uf_sigla"].fillna("") + "|" + grafias["municipio_norm"])
    linhas = []
    for _, grupo in grafias.groupby(identidade, sort=False):
        atual = grupo.sort_values(["max", "min"]).iloc[-1]
        linhas.append({**atual[_CHAVE_GRAFIA].to_dict(),
                       "grafias_senatran": " | ".join(grupo["municipio_norm"])})
    dimensao = pd.DataFrame(linhas).merge(municipios[["cod_municipio_ibge", "municipio_ibge"]],
                                          on="cod_municipio_ibge", how="left")
    dimensao["cod_municipio_ibge"] = dimensao["cod_municipio_ibge"].astype("Int64")
    dimensao["cod_uf_ibge"] = dimensao["cod_uf_ibge"].astype("Int64")
    colunas = ["cod_municipio_ibge", "municipio_ibge", "uf_sigla", "cod_uf_ibge", "regiao",
               "municipio_norm", "grafias_senatran"]
    return (dimensao[colunas].sort_values(["cod_municipio_ibge", "municipio_norm"], na_position="last")
            .reset_index(drop=True))
