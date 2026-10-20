"""Tabela PBE Veicular do Inmetro: propulsão e categoria por versão de veículo leve.

O Programa Brasileiro de Etiquetagem Veicular publica, por ciclo anual, a lista dos
veículos leves ensaiados, com a propulsão declarada pelo fabricante (combustão,
elétrico, híbrido, híbrido plug-in) e a categoria de porte. É a única fonte pública
brasileira que separa PHEV de HEV **por versão** — o campo combustível do RENAVAM não
separa (ver a conciliação no README) e a inferência por nome de modelo erra entre as
duas classes.

Serve a três coisas, e nenhuma delas é substituir as regras de ``dados/modelos.csv``:

* auditar a classificação por nome (um modelo classificado plug-in cuja linha não tem
  versão plug-in no PBE é falso positivo provável);
* dar porte ao que casa, que é meio caminho da lacuna de tipo de veículo;
* respaldar com fonte externa a decisão de deixar híbrido leve fora da frota
  eletrificada: o Inmetro classifica o "Hybrid" 12 V da Stellantis como combustão.

**A fonte é PDF.** Não há CSV no dados.gov.br, e o PDF do ciclo tem o texto desenhado
caractere a caractere: as colunas são recuperadas pelas bordas (retângulos verticais),
não pelo fluxo do texto. Por isso a extração não roda no ``processar``: ela gera um
instantâneo versionado em ``dados/pbev.csv`` (comando ``pbev``), que é o que o resto do
pacote lê. O PDF muda de nome e de URL a cada ciclo, e o leiaute pode mudar com ele —
``extrair_pbev`` falha alto quando o que sai não se parece com a tabela esperada.

Cobertura, que é parcial por construção: só veículo leve novo ensaiado no ciclo. Moto,
scooter, ônibus e caminhão não entram, nem modelo antigo que saiu de linha. A ausência
do PBE não é prova de que o veículo não é leve — mas, depois das equivalências de marca,
é indício.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from .modelos import _PREFIXO, canonizar_marca, carregar_marcas, marca
from .texto import normalizar

log = logging.getLogger(__name__)

PBEV_PADRAO = Path(__file__).parent / "dados" / "pbev.csv"

# Colunas da tabela do PBE, na ordem em que as bordas verticais as delimitam. O
# cabeçalho do PDF é ilegível (rótulos sobrepostos), então a ordem é fixada aqui e
# conferida pelos valores da coluna de propulsão.
COLUNAS_PBEV = ("categoria", "marca", "modelo", "versao", "motor", "propulsao", "transmissao")

# Propulsão declarada no PBE -> classe do pacote. "Plug-in" aparece com as duas caixas.
PROPULSAO_CLASSE = {
    "COMBUSTAO": "combustao",
    "ELETRICO": "eletrico",
    "HIBRIDO": "hibrido",
    "PLUG-IN": "hibrido_plug_in",
}

# Abaixo disto, o que saiu do PDF não é a tabela do ciclo.
MINIMO_VERSOES = 300


def _celulas(pagina) -> list[list[str]]:
    """Linhas de uma página, repartidas pelas bordas verticais da tabela."""
    cortes = sorted({round(r["x0"]) for r in pagina.rects if r["width"] < 2 and r["height"] > 20})
    if len(cortes) < len(COLUNAS_PBEV):
        return []
    cortes.append(max(cortes) + 40)
    linhas: dict[int, list] = {}
    for caractere in pagina.chars:
        linhas.setdefault(round(caractere["top"] / 1.5), []).append(caractere)
    repartidas = []
    for alvo in sorted(linhas):
        celulas = [""] * (len(cortes) - 1)
        for caractere in sorted(linhas[alvo], key=lambda c: c["x0"]):
            coluna = next((i for i in range(len(cortes) - 1)
                           if cortes[i] - 1 <= caractere["x0"] < cortes[i + 1] - 1), None)
            if coluna is not None:
                celulas[coluna] += caractere["text"]
        if sum(bool(c.strip()) for c in celulas) >= len(COLUNAS_PBEV) + 1:
            repartidas.append([c.strip() for c in celulas])
    return repartidas


def extrair_pbev(caminho: str | Path, ciclo: int) -> pd.DataFrame:
    """Extrai a tabela de um PDF de ciclo do PBE Veicular.

    Devolve uma linha por versão, com ``ciclo`` e as colunas de ``COLUNAS_PBEV``.
    Levanta ``ValueError`` quando o que sai do PDF não se parece com a tabela —
    leiaute novo tem de parar a execução, não produzir tabela silenciosamente errada.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("A extração do PDF do PBE precisa do pdfplumber: "
                          "pip install -e \".[pdf]\"") from None
    with pdfplumber.open(caminho) as pdf:
        linhas = [celulas for pagina in pdf.pages for celulas in _celulas(pagina)]
    if not linhas:
        raise ValueError(f"{Path(caminho).name}: nenhuma borda de coluna reconhecida; "
                         "o leiaute do PDF mudou.")
    tabela = pd.DataFrame([linha[:len(COLUNAS_PBEV)] for linha in linhas], columns=list(COLUNAS_PBEV))
    tabela["propulsao_norm"] = tabela["propulsao"].map(normalizar).str.upper()
    tabela = tabela[tabela["propulsao_norm"].isin(PROPULSAO_CLASSE)].copy()
    # Célula que transborda para uma segunda linha visual (transmissão com nome longo:
    # "Automática Dupla", "Embreagem (DCT)") vira uma linha sem marca nem modelo, e o
    # bloco de legenda da primeira página também. Nenhum dos dois é versão.
    fragmentos = (tabela["categoria"] == "") | (tabela["marca"] == "") | (tabela["modelo"] == "")
    log.debug("%s: %d linhas descartadas sem marca ou modelo", Path(caminho).name, fragmentos.sum())
    tabela = tabela[~fragmentos]
    if len(tabela) < MINIMO_VERSOES:
        raise ValueError(f"{Path(caminho).name}: só {len(tabela)} versões reconhecidas "
                         f"(esperadas ao menos {MINIMO_VERSOES}); o leiaute do PDF mudou.")
    tabela["classe"] = tabela["propulsao_norm"].map(PROPULSAO_CLASSE)
    tabela.insert(0, "ciclo", ciclo)
    log.info("%s: %d versões, %d marcas, %d modelos", Path(caminho).name,
             len(tabela), tabela["marca"].nunique(), tabela["modelo"].nunique())
    return (tabela[["ciclo", *COLUNAS_PBEV, "classe"]]
            .sort_values(["marca", "modelo", "versao"]).reset_index(drop=True))


def gravar_pbev(tabela: pd.DataFrame, caminho: str | Path | None = None) -> Path:
    """Grava o instantâneo do PBE, substituindo o ciclo se ele já estiver no arquivo."""
    caminho = Path(caminho) if caminho is not None else PBEV_PADRAO
    if caminho.exists():
        anterior = pd.read_csv(caminho, sep=";", dtype={"ciclo": int}, keep_default_na=False,
                               encoding="utf-8")
        tabela = pd.concat([anterior[~anterior["ciclo"].isin(tabela["ciclo"])], tabela],
                           ignore_index=True)
    tabela.sort_values(["ciclo", "marca", "modelo", "versao"]).to_csv(
        caminho, sep=";", index=False, encoding="utf-8")
    return caminho


def carregar_pbev(caminho: str | Path | None = None) -> pd.DataFrame:
    """Lê o instantâneo versionado do PBE Veicular."""
    caminho = Path(caminho) if caminho is not None else PBEV_PADRAO
    tabela = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8")
    tabela["ciclo"] = tabela["ciclo"].astype(int)
    invalidas = set(tabela["classe"]) - set(PROPULSAO_CLASSE.values())
    if invalidas:
        raise ValueError(f"Classes desconhecidas em {caminho.name}: {sorted(invalidas)}")
    return tabela


# --- junção com a base por modelo ---------------------------------------------------------

_NAO_ALFANUMERICO = re.compile(r"[^A-Z0-9]")


def _chave(marcas: pd.Series, modelo: pd.Series, equivalencias: pd.Series) -> pd.Series:
    """Chave de junção: marca canônica + modelo sem espaço nem pontuação.

    Tirar espaço e pontuação do modelo faz ``TIGGO 8`` do PBE encontrar ``TIGGO8`` do
    RENAVAM, que é a diferença mais comum entre as duas grafias.
    """
    marca_canonica = canonizar_marca(marcas.map(normalizar).str.upper(), equivalencias)
    return marca_canonica + "|" + modelo.map(normalizar).str.upper().map(
        lambda m: _NAO_ALFANUMERICO.sub("", m))


def _texto_do_modelo(marca_modelo_norm: pd.Series) -> pd.Series:
    """O que vem depois da marca no texto do RENAVAM.

    ``TOYOTA/COROLLA ALTIS HV`` -> ``COROLLA ALTIS HV``;
    ``I/CAOACHERY TIGGO8 PHEV`` -> ``TIGGO8 PHEV``.
    """
    resto = marca_modelo_norm.astype("string").str.replace(_PREFIXO, "", regex=True)
    com_barra = resto.str.extract(r"^[^/]+/(.*)$", expand=False)
    return com_barra.fillna(resto.str.replace(r"^[^/ ]+\s*", "", regex=True)).str.strip()


def _candidatos(texto: str, maximo: int = 3) -> list[str]:
    """Chaves de modelo a tentar, da mais específica para a menos.

    ``TIGGO8 PRO HA`` rende ``TIGGO8PROHA``, ``TIGGO8PRO`` e ``TIGGO8``: o PBE grafa
    ``Tiggo 8 Pro`` e o RENAVAM abrevia, então vence o casamento mais longo.
    """
    palavras = texto.split()[:maximo]
    return [_NAO_ALFANUMERICO.sub("", "".join(palavras[:k])) for k in range(len(palavras), 0, -1)]


CLASSES_ELETRIFICADAS_PBEV = ("eletrico", "hibrido", "hibrido_plug_in")


def _aviso(classe: str, classes_pbe: str) -> str:
    """A divergência entre a classe atribuída e o conjunto de classes do PBE."""
    if not classes_pbe or classe == "hibrido_leve":
        return ""
    do_pbe = classes_pbe.split("|")
    if classe in do_pbe:
        return ""
    if classe in CLASSES_ELETRIFICADAS_PBEV:
        return "sem_versao_no_pbe"
    if all(c in CLASSES_ELETRIFICADAS_PBEV for c in do_pbe):
        return "pbe_so_eletrificado"
    return ""


def auditar_com_pbev(classificados: pd.DataFrame, propulsoes: pd.DataFrame,
                     equivalencias: pd.Series | None = None) -> pd.DataFrame:
    """Confronta a classificação por nome com a propulsão declarada no PBE Veicular.

    Acrescenta, por modelo:

    ``pbe_classes``
        classes que a linha do modelo tem no PBE, separadas por ``|``. Vazio quando o
        modelo não casou com nenhuma linha do PBE — o que é esperado em moto, ônibus,
        caminhão e modelo fora de linha, e não é erro.
    ``pbe_categoria``
        categoria de porte do PBE (Médio, Picape, Utilitário Esportivo Compacto...).
    ``pbe_aviso``
        a divergência, quando há, **com a direção**, porque as duas direções se leem de
        formas opostas:

        ``sem_versao_no_pbe``
            a regra atribuiu uma classe eletrificada que o PBE não registra para aquele
            modelo. Falso positivo provável da regra — é a fila mais acionável.
        ``pbe_so_eletrificado``
            a regra disse combustão e **toda** versão do modelo no PBE é eletrificada
            (``I/HONDA CR-V LX`` com a linha CR-V só híbrida). Pode ser regra faltando,
            mas pode ser geração antiga: o PBE do ciclo só traz o que está em linha, e
            ``I/MMC OUTLANDER 2.0`` é o Outlander a combustão de antes do PHEV. Confira
            o ano de fabricação antes de criar regra.

    A junção é por marca canônica e nome de modelo, nunca reduzindo o modelo a uma
    propulsão só: o aviso olha o **conjunto** de classes do modelo, então Corolla a
    combustão e Corolla Hybrid conviverem na mesma linha do PBE não gera acusação falsa.

    ``hibrido_leve`` nunca gera aviso: o PBE não tem essa categoria e registra o híbrido
    leve de 12 V como combustão (e o de 48 V, às vezes, como híbrido). A ausência de
    aviso aqui é o respaldo externo de deixá-lo fora da frota eletrificada, não um
    casamento.
    """
    equivalencias = carregar_marcas() if equivalencias is None else equivalencias
    indice = propulsoes.set_index("chave")
    marcas = marca(classificados["marca_modelo_norm"], equivalencias)
    modelos = _texto_do_modelo(classificados["marca_modelo_norm"])
    chaves = []
    for marca_canonica, texto in zip(marcas, modelos):
        achada = ""
        if isinstance(marca_canonica, str) and isinstance(texto, str):
            achada = next((c for c in (f"{marca_canonica}|{m}" for m in _candidatos(texto))
                           if c in indice.index), "")
        chaves.append(achada)
    casadas = pd.Series(chaves, index=classificados.index)
    auditado = classificados.copy()
    auditado["pbe_classes"] = casadas.map(indice["pbe_classes"]).fillna("")
    auditado["pbe_categoria"] = casadas.map(indice["pbe_categoria"]).fillna("")
    auditado["pbe_aviso"] = [_aviso(classe, classes)
                             for classe, classes in zip(auditado["classe"], auditado["pbe_classes"])]
    return auditado


def propulsoes_por_modelo(pbev: pd.DataFrame, ciclo: int | None = None,
                          equivalencias: pd.Series | None = None) -> pd.DataFrame:
    """Classes que cada modelo do PBE tem, por chave de junção.

    Um modelo pode existir em mais de uma propulsão (Corolla tem versão a combustão e
    versão híbrida; Haval H6 tem HEV e PHEV). Por isso o resultado guarda o **conjunto**
    de classes, não uma classe só: reduzir a uma — pela moda, por exemplo — faz a tabela
    afirmar que o Corolla é a combustão e contradizer a classificação correta do
    Corolla Hybrid.
    """
    equivalencias = carregar_marcas() if equivalencias is None else equivalencias
    # Um ciclo só, o mais recente por padrão: unir ciclos acumularia a propulsão de
    # gerações diferentes do mesmo nome de modelo e enfraqueceria o aviso.
    ciclo = int(pbev["ciclo"].max()) if ciclo is None else ciclo
    pbev = pbev[pbev["ciclo"] == ciclo]
    if pbev.empty:
        raise ValueError(f"Nenhuma versão do PBE para o ciclo {ciclo}.")
    com_chave = pbev.assign(chave=_chave(pbev["marca"], pbev["modelo"], equivalencias))
    return (com_chave.groupby("chave")
            .agg(pbe_classes=("classe", lambda s: "|".join(sorted(set(s)))),
                 pbe_categoria=("categoria", lambda s: s.mode().iat[0]),
                 pbe_versoes=("versao", "size"))
            .reset_index())
