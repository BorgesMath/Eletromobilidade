"""Leitura e padronização dos arquivos de frota da SENATRAN.

Arquivo-alvo: "Frota por UF, Município e Combustível" (mensal), publicado em
``.xlsx`` com as colunas ``UF | Município | Combustível Veículo | Qtd. Veículos``.
O leitor também aceita ``.csv``/``.txt`` (``;`` ou ``,``; UTF-8 ou Latin-1) e
``.zip`` contendo um desses formatos, e tolera linhas de título acima do cabeçalho.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from .texto import normalizar, normalizar_coluna

COLUNAS = ("uf", "municipio", "combustivel", "qtd_veiculos")
EXTENSOES_DADOS = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".zip")

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "MARO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
    "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}
# "MARO" aparece em nomes de arquivo do portal em que o "ç" de "Março" foi perdido.

_LINHAS_BUSCA_CABECALHO = 30


def inferir_periodo(nome: str | Path) -> tuple[int, int] | None:
    """Extrai ``(ano, mês)`` de um nome de arquivo ou texto; ``None`` se não for possível.

    Reconhece o nome do mês por extenso (``..._Julho_2026.xlsx``) ou o padrão
    numérico ``AAAA-MM``/``AAAA_MM``.
    """
    nome = nome.name if isinstance(nome, Path) else str(nome)
    texto = re.sub(r"[^A-Z0-9]+", " ", normalizar(nome))
    tokens = texto.split()
    anos = [int(t) for t in tokens if re.fullmatch(r"(19|20)\d{2}", t)]
    meses = [MESES[t] for t in tokens if t in MESES]
    if len(set(anos)) == 1 and len(set(meses)) == 1:
        return anos[0], meses[0]
    numerico = re.search(r"\b((?:19|20)\d{2}) (0[1-9]|1[0-2])\b", texto)
    if numerico:
        return int(numerico.group(1)), int(numerico.group(2))
    return None


def _mapear_colunas(colunas: list[object]) -> dict[object, str]:
    """Associa cada coluna original a um nome canônico de ``COLUNAS``."""
    mapa: dict[object, str] = {}
    for original in colunas:
        nome = normalizar_coluna(original)
        if "combust" in nome:
            canonico = "combustivel"
        elif "municip" in nome:
            canonico = "municipio"
        elif nome in ("uf", "sigla_uf", "estado", "unidade_federativa"):
            canonico = "uf"
        elif nome.startswith("qtd") or "quantidade" in nome or nome in ("veiculos", "total"):
            canonico = "qtd_veiculos"
        else:
            continue
        if canonico not in mapa.values():
            mapa[original] = canonico
    return mapa


def _linha_cabecalho(amostra: pd.DataFrame) -> int:
    for i, linha in amostra.iterrows():
        if set(_mapear_colunas(list(linha.values)).values()) == set(COLUNAS):
            return int(i)
    raise ValueError(
        "Cabeçalho não encontrado: esperadas colunas de UF, Município, Combustível e Qtd. Veículos "
        f"nas primeiras {_LINHAS_BUSCA_CABECALHO} linhas."
    )


def _ler_excel(origem) -> pd.DataFrame:
    amostra = pd.read_excel(origem, header=None, nrows=_LINHAS_BUSCA_CABECALHO, dtype=object)
    if hasattr(origem, "seek"):
        origem.seek(0)
    return pd.read_excel(origem, header=_linha_cabecalho(amostra), dtype=object)


def _decodificar(conteudo: bytes) -> str:
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ValueError("Codificação de texto não reconhecida.")


def _ler_texto(conteudo: bytes) -> pd.DataFrame:
    texto = _decodificar(conteudo)
    linhas = texto.splitlines()[:_LINHAS_BUSCA_CABECALHO]
    separador = max((";", ",", "\t"), key=lambda s: sum(l.count(s) for l in linhas))
    amostra = pd.read_csv(io.StringIO("\n".join(linhas)), sep=separador, header=None, dtype=str,
                          on_bad_lines="skip", engine="python")
    cabecalho = _linha_cabecalho(amostra)
    return pd.read_csv(io.StringIO(texto), sep=separador, skiprows=cabecalho, dtype=str,
                       keep_default_na=False)


def _ler_bruto(caminho: Path) -> pd.DataFrame:
    sufixo = caminho.suffix.lower()
    if sufixo in (".xlsx", ".xlsm", ".xls"):
        return _ler_excel(caminho)
    if sufixo in (".csv", ".txt"):
        return _ler_texto(caminho.read_bytes())
    if sufixo == ".zip":
        with zipfile.ZipFile(caminho) as z:
            membros = [m for m in z.namelist()
                       if Path(m).suffix.lower() in EXTENSOES_DADOS[:-1] and not m.startswith("__MACOSX")]
            if len(membros) != 1:
                raise ValueError(f"{caminho.name}: esperado 1 arquivo de dados no zip, encontrados {membros}")
            conteudo = z.read(membros[0])
        if Path(membros[0]).suffix.lower() in (".xlsx", ".xlsm", ".xls"):
            return _ler_excel(io.BytesIO(conteudo))
        return _ler_texto(conteudo)
    raise ValueError(f"Formato não suportado: {caminho.name}")


_MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+$")


def para_inteiro(valores: pd.Series) -> pd.Series:
    """Converte contagens para inteiro (``Int64``).

    Aceita números nativos do Excel, texto como ``" 7.0"`` (exportação com
    ponto decimal) e ``"1.234.567"`` (ponto como separador de milhar). Contagens
    não inteiras ou negativas geram erro, pois indicam leitura incorreta.
    """
    def converter(v):
        if v is None or (isinstance(v, float) and v != v):
            return None
        if isinstance(v, (int, float)):
            return v
        s = str(v).strip().replace(" ", "")
        if not s or s == "-":
            return None
        if _MILHAR.match(s):
            return float(s.replace(".", ""))
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        return float(s)

    numeros = pd.to_numeric(valores.map(converter), errors="raise")
    validos = numeros.dropna()
    if ((validos % 1) != 0).any() or (validos < 0).any():
        exemplos = valores[numeros.notna() & (((numeros % 1) != 0) | (numeros < 0))].head(5).tolist()
        raise ValueError(f"Contagens não inteiras ou negativas: {exemplos}")
    return numeros.round().astype("Int64")


def ler_frota_combustivel(caminho: str | Path) -> pd.DataFrame:
    """Lê um arquivo de frota por município e combustível e devolve as colunas de ``COLUNAS``.

    Linhas de total e linhas totalmente vazias são descartadas; os rótulos de
    texto são preservados como publicados (apenas com espaços aparados).
    """
    caminho = Path(caminho)
    bruto = _ler_bruto(caminho)
    df = bruto.rename(columns=_mapear_colunas(list(bruto.columns)))[list(COLUNAS)]

    for col in ("uf", "municipio", "combustivel"):
        df[col] = df[col].map(lambda v: None if v is None or (isinstance(v, float) and v != v)
                              else str(v).strip() or None)
    df = df.dropna(how="all")
    eh_total = df["uf"].map(normalizar).str.startswith("TOTAL") | df["municipio"].map(normalizar).eq("TOTAL")
    df = df[~eh_total & df["combustivel"].notna()].copy()
    df["qtd_veiculos"] = para_inteiro(df["qtd_veiculos"])
    return df.reset_index(drop=True)
