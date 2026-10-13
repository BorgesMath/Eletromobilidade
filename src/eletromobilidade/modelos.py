"""Classificação do texto "Marca Modelo" do RENAVAM em classes de tecnologia de tração.

O arquivo de frota por marca/modelo não informa o combustível; a tecnologia é
inferida do nome do modelo por regras ordenadas em ``dados/modelos.csv``
(``classe;padrao;nota``, separador ``;``). A primeira regra cujo padrão (regex,
aplicado ao texto normalizado) casa define a classe. Sem regra, a classe é
``combustao``. Cada linha classificada registra o número da regra usada, para
auditoria.

As regras específicas por marca vêm antes das genéricas porque os nomes têm
armadilhas: ``VW/8.150E DELIVERY`` (diesel; "E" = eletrônico), ``VW/POLO 1.6
E-FLEX`` (flex), ``HYUNDAI/HB20 EVOLUTION`` e ``CHEV/...`` contêm "EV"/"HEV".
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pandas as pd

from .texto import normalizar

CLASSES_MODELO = ("eletrico", "hibrido_plug_in", "hibrido", "hibrido_leve", "celula_combustivel",
                  "combustao", "nao_motorizado", "sem_informacao")
# Híbridos leves (12/48 V) não tracionam só com o motor elétrico e ficam fora do total eletrificado;
# aparecem em coluna própria nos painéis.
CLASSES_ELETRIFICADAS_MODELO = ("eletrico", "hibrido_plug_in", "hibrido", "celula_combustivel")

REGRAS_PADRAO = Path(__file__).parent / "dados" / "modelos.csv"

# Marcas cuja linha no Brasil é (quase) toda eletrificada: um modelo dessas marcas
# classificado como combustão provavelmente é uma regra faltando.
MARCAS_A_REVISAR = ("BYD", "TESLA", "VOLTZ", "ZEEKR", "POLESTAR", "NETA", "AION", "XPENG", "GWM", "OMODA",
                    "JAECOO", "GAC", "LEAPMOTOR", "SERES")


def carregar_regras(caminho: str | Path | None = None) -> pd.DataFrame:
    """Lê e valida as regras; devolve ``regra`` (número da linha, a partir de 1), ``classe``, ``padrao``, ``nota``."""
    caminho = Path(caminho) if caminho is not None else REGRAS_PADRAO
    regras = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8")
    invalidas = set(regras["classe"]) - set(CLASSES_MODELO)
    if invalidas:
        raise ValueError(f"Classes desconhecidas em {caminho}: {sorted(invalidas)}")
    regras.insert(0, "regra", range(1, len(regras) + 1))
    for numero, padrao in zip(regras["regra"], regras["padrao"]):
        try:
            re.compile(padrao)
        except re.error as erro:
            raise ValueError(f"Regra {numero} de {caminho}: regex inválida ({erro})") from None
    return regras


def classificar_modelos(modelos: pd.Series, regras: pd.DataFrame | None = None) -> pd.DataFrame:
    """Classifica textos de "Marca Modelo".

    Retorna um DataFrame alinhado ao índice de entrada com ``marca_modelo_norm``,
    ``classe``, ``regra`` (0 = nenhuma regra, classe padrão) e ``eletrificado``.
    O cálculo é feito uma vez por texto distinto.
    """
    regras = carregar_regras() if regras is None else regras
    unicos = pd.Series(pd.unique(modelos.astype("string").fillna("")), dtype="string")
    norm = unicos.map(normalizar).astype("string")
    classe = pd.Series("combustao", index=norm.index, dtype="string")
    regra = pd.Series(0, index=norm.index, dtype="int64")
    classe[norm == ""] = "sem_informacao"
    pendente = norm != ""
    for numero, cls, padrao in regras[["regra", "classe", "padrao"]].itertuples(index=False):
        if not pendente.any():
            break
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "This pattern is interpreted as a regular expression")
            casou = pendente & norm.str.contains(padrao, regex=True)
        classe[casou] = cls
        regra[casou] = numero
        pendente &= ~casou
    mapa = pd.DataFrame({"marca_modelo_norm": norm.values, "classe": classe.values, "regra": regra.values},
                        index=unicos.values)
    resultado = mapa.reindex(modelos.astype("string").fillna("").values)
    resultado.index = modelos.index
    resultado["eletrificado"] = resultado["classe"].isin(CLASSES_ELETRIFICADAS_MODELO)
    return resultado


def marca(marca_modelo_norm: pd.Series) -> pd.Series:
    """Marca extraída do texto normalizado (sem o prefixo ``I/``/``IMP/`` de importado)."""
    return (marca_modelo_norm.str.replace(r"^(I|IMP)/", "", regex=True)
            .str.extract(r"^([^/ ]+)", expand=False))


def a_revisar(classificados: pd.DataFrame) -> pd.Series:
    """Modelos de marcas eletrificadas que não casaram com nenhuma regra."""
    return (classificados["regra"].eq(0)
            & marca(classificados["marca_modelo_norm"]).isin(MARCAS_A_REVISAR))


class ClassificadorModelos:
    """``classificar_modelos`` com memória: cada texto distinto é classificado uma única vez.

    Útil na leitura em blocos, em que o mesmo modelo se repete em todos os blocos.
    """

    def __init__(self, regras: pd.DataFrame | None = None):
        self.regras = carregar_regras() if regras is None else regras
        self._cache = pd.DataFrame(columns=["marca_modelo_norm", "classe", "regra", "eletrificado"])

    def __call__(self, modelos: pd.Series) -> pd.DataFrame:
        chaves = modelos.astype("string").fillna("")
        novos = pd.Series(pd.unique(chaves[~chaves.isin(self._cache.index)]), dtype="string")
        if len(novos):
            classificados = classificar_modelos(novos, self.regras)
            classificados.index = novos.values
            self._cache = pd.concat([self._cache, classificados]) if len(self._cache) else classificados
        resultado = self._cache.reindex(chaves.values)
        resultado.index = modelos.index
        return resultado

    @property
    def classificados(self) -> pd.DataFrame:
        """Todos os textos vistos até agora, com a classificação atribuída."""
        return self._cache.rename_axis("marca_modelo").reset_index()
