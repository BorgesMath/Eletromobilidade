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

Do mesmo texto sai a marca, que o RENAVAM não normaliza: ela é extraída por
posição (``marca_renavam``) e depois passada pela tabela de equivalência
``dados/marcas.csv`` (``marca``), que une as grafias da mesma empresa.
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
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if linha.strip() and linha.count(";") != 2:
            raise ValueError(f"{caminho.name}, linha {numero}: esperados 3 campos separados por ';' "
                             f"(não use ';' dentro da regex nem da nota): {linha[:80]}")
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


# --- marca -------------------------------------------------------------------------------

# O primeiro elemento de "Marca Modelo" não é sempre a marca. Pode ser um marcador de
# importação ou a montadora que montou o veículo no Brasil (``JTA/SUZUKI EN125 YES``), e
# nesses casos a marca vem depois; ou o tipo do veículo, em reboque e máquina
# (``SR/RANDON SR CA``, ``M.A./MASSEY-FERGUSON``), e aí o que vem depois é o fabricante.
PREFIXOS_MONTADORA = ("I", "IMP", "JTA")
PREFIXOS_TIPO = ("R", "SR", "REB", "MR", "MO", "M.A.")
_PREFIXO = re.compile("^(?:" + "|".join(re.escape(p) for p in PREFIXOS_MONTADORA + PREFIXOS_TIPO) + ")/")

# Textos em que a marca não existe, e não é só uma grafia a normalizar.
SEM_MARCA = ("", "SEM INFORMACAO")

_SEM_PONTUACAO = re.compile(r"[^A-Z0-9]")

MARCAS_PADRAO = Path(__file__).parent / "dados" / "marcas.csv"


def carregar_marcas(caminho: str | Path | None = None) -> pd.Series:
    """Lê a tabela de equivalência de marcas; devolve ``marca_renavam`` -> ``marca``.

    Valida que nenhuma grafia aparece duas vezes e que nenhuma forma canônica é, ela
    mesma, uma grafia a normalizar (o que faria o mapeamento depender da ordem).
    """
    caminho = Path(caminho) if caminho is not None else MARCAS_PADRAO
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if linha.strip() and linha.count(";") != 2:
            raise ValueError(f"{caminho.name}, linha {numero}: esperados 3 campos separados por ';' "
                             f"(não use ';' dentro da nota): {linha[:80]}")
    tabela = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8")
    repetidas = tabela["marca_renavam"][tabela["marca_renavam"].duplicated()]
    if len(repetidas):
        raise ValueError(f"Grafias repetidas em {caminho.name}: {sorted(set(repetidas))}")
    equivalencias = tabela.set_index("marca_renavam")["marca"]
    encadeadas = set(equivalencias.values) & set(equivalencias.index)
    if encadeadas:
        raise ValueError(f"Formas canônicas que também são grafias a normalizar em {caminho.name}: "
                         f"{sorted(encadeadas)}")
    reduzida = equivalencias.groupby(equivalencias.index.map(_reduzir)).nunique()
    if (reduzida > 1).any():
        colidem = sorted(reduzida[reduzida > 1].index)
        raise ValueError(f"Grafias que colidem ao tirar pontuação e espaço, com formas canônicas "
                         f"diferentes, em {caminho.name}: {colidem}")
    return equivalencias


def _reduzir(grafia: str) -> str:
    """A grafia sem pontuação nem espaço, para comparar formas que só diferem nisso."""
    return _SEM_PONTUACAO.sub("", grafia)


def canonizar_marca(grafias: pd.Series, equivalencias: pd.Series | None = None) -> pd.Series:
    """Aplica a tabela de equivalência a grafias de marca já extraídas.

    O casamento ignora pontuação e espaço, para que a grafia do Inmetro
    (``CAOA CHERY``) encontre a entrada escrita como o RENAVAM grafa
    (``CAOACHERY``) sem precisar de duas linhas na tabela. Grafia fora da tabela
    é devolvida como está.
    """
    equivalencias = carregar_marcas() if equivalencias is None else equivalencias
    reduzidas = dict(zip((_reduzir(g) for g in equivalencias.index), equivalencias.values))
    canonicas = grafias.map(lambda g: reduzidas.get(_reduzir(g)) if isinstance(g, str) else None)
    return canonicas.astype("string").fillna(grafias)


def marca_renavam(marca_modelo_norm: pd.Series) -> pd.Series:
    """Marca como o RENAVAM grafa, sem o prefixo de montadora ou de tipo de veículo.

    Havendo ``/`` no restante, a marca é tudo o que vem antes (``HARLEY DAVIDSON/XL883N``
    -> ``HARLEY DAVIDSON``); não havendo, é a primeira palavra (``I/BYD DOLPHIN GS 180EV``
    -> ``BYD``). Nula quando não há marca no texto.
    """
    resto = marca_modelo_norm.astype("string").str.replace(_PREFIXO, "", regex=True)
    bruta = (resto.str.extract(r"^([^/]+)/", expand=False)
             .fillna(resto.str.extract(r"^([^/ ]+)", expand=False))
             .str.strip())
    return bruta.mask(bruta.isin(SEM_MARCA) | resto.isin(SEM_MARCA))


def marca(marca_modelo_norm: pd.Series, equivalencias: pd.Series | None = None) -> pd.Series:
    """Marca canônica: ``marca_renavam`` passada pela tabela de equivalência.

    Grafia fora da tabela segue como está — o resíduo é listado por
    ``marcas_sem_equivalencia``, não silenciado.
    """
    bruta = marca_renavam(marca_modelo_norm)
    return canonizar_marca(bruta, equivalencias)


_MINIMO_PREFIXO = 4


def _parecida_com(frota: pd.Series) -> dict[str, str]:
    """Para cada grafia, a grafia de que ela parece ser variante (ou nada).

    Duas pistas textuais, sempre apontando da grafia menos frequente para a mais
    frequente, que é a candidata a forma boa:

    * começar por outra grafia, que é o caso do modelo colado na marca
      (``FIATDUCATO`` -> ``FIAT``, ``SCANIA-VABIS`` -> ``SCANIA``);
    * coincidir com outra tirando pontuação e espaço (``MERCEDES BENZ`` ->
      ``MERCEDES-BENZ``).

    Abreviação sem parentesco no texto (``GM`` -> Chevrolet, ``MMC`` ->
    Mitsubishi) não sai daqui: só a olho, em ``dados/marcas.csv``.
    """
    achados: dict[str, str] = {}
    reduzidas: dict[str, str] = {}
    for g in frota.sort_values(ascending=False).index:
        reduzidas.setdefault(re.sub(r"[^A-Z0-9]", "", g), g)
    for g in frota.index:
        candidata = reduzidas[re.sub(r"[^A-Z0-9]", "", g)]
        if candidata != g:
            achados[g] = candidata
    pilha: list[str] = []
    for g in sorted(frota.index):
        while pilha and not g.startswith(pilha[-1]):
            pilha.pop()
        if pilha and len(pilha[-1]) >= _MINIMO_PREFIXO and frota[pilha[-1]] > frota[g]:
            achados.setdefault(g, pilha[-1])
        pilha.append(g)
    return achados


def marcas_suspeitas(classificados: pd.DataFrame,
                     equivalencias: pd.Series | None = None) -> pd.DataFrame:
    """Grafias fora da tabela de equivalência que parecem variante de outra grafia.

    Fila de trabalho para ampliar ``dados/marcas.csv``, por frota decrescente. Não
    lista toda grafia ausente: a maioria das milhares de grafias do RENAVAM é marca
    de verdade e não precisa de linha na tabela. Ver ``_parecida_com`` para o que
    conta como pista.
    """
    equivalencias = carregar_marcas() if equivalencias is None else equivalencias
    bruta = marca_renavam(classificados["marca_modelo_norm"])
    por_grafia = (classificados.assign(marca_renavam=bruta).dropna(subset=["marca_renavam"])
                  .groupby("marca_renavam", observed=True)
                  .agg(qtd_veiculos=("qtd_veiculos", "sum"), modelos=("marca_modelo_norm", "nunique")))
    parecidas = _parecida_com(por_grafia["qtd_veiculos"])
    # Grafia já resolvida pela tabela não é trabalho, seja como grafia de entrada
    # (CHEV) ou como forma canônica de chegada (MERCEDES-BENZ).
    resolvidas = set(equivalencias.index) | set(equivalencias.values)
    suspeitas = por_grafia.loc[[g for g in por_grafia.index
                                if g in parecidas and g not in resolvidas]]
    return (suspeitas.assign(parecida_com=[parecidas[g] for g in suspeitas.index])
            .sort_values("qtd_veiculos", ascending=False).reset_index())


def dimensao_modelo(marca_modelo: pd.Series, equivalencias: pd.Series | None = None) -> pd.DataFrame:
    """Dimensão de marca e modelo: um registro por texto distinto de "Marca Modelo".

    ``importado`` vem do prefixo ``I/``/``IMP/``, que o RENAVAM usa para veículo
    importado. É a tabela que o painel lê como ``dModelo``, para que a marca seja
    derivada num lugar só, com teste.
    """
    equivalencias = carregar_marcas() if equivalencias is None else equivalencias
    unicos = pd.Series(pd.unique(marca_modelo.dropna().astype("string")), dtype="string")
    norm = unicos.map(normalizar).astype("string")
    importado = norm.str.match(r"^(I|IMP)/").fillna(False)
    return pd.DataFrame({
        "marca_modelo": unicos,
        "marca_modelo_norm": norm,
        "marca_renavam": marca_renavam(norm),
        "marca": marca(norm, equivalencias),
        "importado": importado,
        "origem": pd.Series(["Importado" if i else "Nacional" for i in importado], dtype="string"),
    }).sort_values("marca_modelo").reset_index(drop=True)


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
