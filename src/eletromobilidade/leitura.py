"""Leitura e padronização dos arquivos de frota da SENATRAN.

Dois leiautes:

* "Frota por UF, Município e Combustível" (mensal, ``.xlsx``):
  ``UF | Município | Combustível Veículo | Qtd. Veículos``.
* "Frota por UF, Município, Marca e Modelo, Ano" (mensal, ``.zip`` com texto
  ``;``, ~22 milhões de linhas):
  ``UF | Município | Marca Modelo | Ano Fabricação Veículo CRV | Qtd. Veículos``.
  Lido em blocos, sem carregar o arquivo inteiro na memória.

Os leitores aceitam ``.xlsx``, ``.csv``/``.txt`` (``;``, ``,`` ou tabulação;
UTF-8 ou Latin-1) e ``.zip`` contendo um desses formatos, e toleram linhas de
título acima do cabeçalho.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .texto import normalizar, normalizar_coluna

COLUNAS_COMBUSTIVEL = ("uf", "municipio", "combustivel", "qtd_veiculos")
COLUNAS_MARCA_MODELO = ("uf", "municipio", "marca_modelo", "ano_fabricacao", "qtd_veiculos")
EXTENSOES_DADOS = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".zip")
_EXTENSOES_EXCEL = (".xlsx", ".xlsm", ".xls")

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "MARO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
    "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}
# "MARO" aparece em nomes de arquivo do portal em que o "ç" de "Março" foi perdido.

_LINHAS_BUSCA_CABECALHO = 30
_BYTES_AMOSTRA = 1 << 16


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


def identificar_tabela(texto: str) -> str:
    """Tabela da SENATRAN a que um nome de arquivo ou título se refere.

    ``"combustivel"``, ``"marca_modelo"``, ``"municipio_tipo"``, ``"uf_tipo"`` ou ``"outro"``.
    """
    t = normalizar(texto).replace("_", " ")
    if "COMBUSTIVEL" in t:
        return "combustivel"
    if "MARCA" in t or "MODELO" in t:
        return "marca_modelo"
    if "TIPO" in t:
        return "municipio_tipo" if "MUNICIPIO" in t else "uf_tipo"
    return "outro"


def _mapear_colunas(colunas: list[object]) -> dict[object, str]:
    """Associa cada coluna original a um nome canônico (primeira ocorrência vence)."""
    mapa: dict[object, str] = {}
    for original in colunas:
        nome = normalizar_coluna(original)
        if "combust" in nome:
            canonico = "combustivel"
        elif "municip" in nome:
            canonico = "municipio"
        elif "marca" in nome or "modelo" in nome:
            canonico = "marca_modelo"
        elif nome.startswith("ano"):
            canonico = "ano_fabricacao"
        elif nome in ("uf", "sigla_uf", "estado", "unidade_federativa"):
            canonico = "uf"
        elif nome.startswith("qtd") or "quantidade" in nome or nome in ("veiculos", "total"):
            canonico = "qtd_veiculos"
        else:
            continue
        if canonico not in mapa.values():
            mapa[original] = canonico
    return mapa


def _linha_cabecalho(amostra: pd.DataFrame, colunas: tuple[str, ...]) -> int:
    for i, linha in amostra.iterrows():
        if set(colunas) <= set(_mapear_colunas(list(linha.values)).values()):
            return int(i)
    raise ValueError(f"Cabeçalho não encontrado: esperadas as colunas {colunas} "
                     f"nas primeiras {_LINHAS_BUSCA_CABECALHO} linhas.")


# --- acesso aos bytes (arquivo simples ou membro de zip) ------------------------------

def _membro_zip(z: zipfile.ZipFile, nome_zip: str) -> str:
    membros = [m for m in z.namelist()
               if Path(m).suffix.lower() in EXTENSOES_DADOS[:-1] and not m.startswith("__MACOSX")]
    if len(membros) != 1:
        raise ValueError(f"{nome_zip}: esperado 1 arquivo de dados no zip, encontrados {membros}")
    return membros[0]


@contextmanager
def _abrir_binario(caminho: Path):
    """Abre o arquivo de dados (ou o único arquivo de dados dentro do zip) em modo binário.

    Devolve ``(arquivo, nome_interno)``.
    """
    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as z:
            membro = _membro_zip(z, caminho.name)
            with z.open(membro) as f:
                yield f, membro
    else:
        with open(caminho, "rb") as f:
            yield f, caminho.name


def _detectar_codificacao(amostra: bytes) -> str:
    # Descarta a última linha da amostra, que pode ter um caractere multibyte cortado.
    amostra = amostra[: amostra.rfind(b"\n") + 1] or amostra
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            amostra.decode(codificacao)
            return codificacao
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _detectar_texto(caminho: Path, colunas: tuple[str, ...]) -> tuple[str, str, int]:
    """Codificação, separador e índice da linha de cabeçalho de um arquivo de texto."""
    with _abrir_binario(caminho) as (f, _):
        amostra = f.read(_BYTES_AMOSTRA)
    codificacao = _detectar_codificacao(amostra)
    linhas = amostra.decode(codificacao, errors="replace").splitlines()[:_LINHAS_BUSCA_CABECALHO]
    separador = max((";", ",", "\t"), key=lambda s: sum(l.count(s) for l in linhas))
    tabela = pd.read_csv(io.StringIO("\n".join(linhas)), sep=separador, header=None, dtype=str,
                         on_bad_lines="skip", engine="python")
    return codificacao, separador, _linha_cabecalho(tabela, colunas)


def _eh_excel(caminho: Path) -> bool:
    if caminho.suffix.lower() in _EXTENSOES_EXCEL:
        return True
    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as z:
            return Path(_membro_zip(z, caminho.name)).suffix.lower() in _EXTENSOES_EXCEL
    return False


def _ler_excel(caminho: Path, colunas: tuple[str, ...]) -> pd.DataFrame:
    with _abrir_binario(caminho) as (f, _):
        conteudo = io.BytesIO(f.read())
    amostra = pd.read_excel(conteudo, header=None, nrows=_LINHAS_BUSCA_CABECALHO, dtype=object)
    conteudo.seek(0)
    return pd.read_excel(conteudo, header=_linha_cabecalho(amostra, colunas), dtype=object)


def _ler_texto_em_blocos(caminho: Path, colunas: tuple[str, ...],
                         tamanho_bloco: int | None) -> Iterator[pd.DataFrame]:
    codificacao, separador, cabecalho = _detectar_texto(caminho, colunas)
    opcoes = dict(sep=separador, skiprows=cabecalho, dtype=str, keep_default_na=False)
    with _abrir_binario(caminho) as (f, _):
        texto = io.TextIOWrapper(f, encoding=codificacao, newline="")
        if tamanho_bloco is None:
            yield pd.read_csv(texto, **opcoes)
        else:
            yield from pd.read_csv(texto, chunksize=tamanho_bloco, **opcoes)


def _ler_blocos(caminho: Path, colunas: tuple[str, ...], tamanho_bloco: int | None) -> Iterator[pd.DataFrame]:
    if caminho.suffix.lower() not in EXTENSOES_DADOS:
        raise ValueError(f"Formato não suportado: {caminho.name}")
    if _eh_excel(caminho):
        yield _ler_excel(caminho, colunas)
    else:
        yield from _ler_texto_em_blocos(caminho, colunas, tamanho_bloco)


# --- conversões ----------------------------------------------------------------------

def para_inteiro(valores: pd.Series) -> pd.Series:
    """Converte contagens para inteiro (``Int64``), de forma vetorizada.

    Aceita números nativos do Excel, texto como ``" 7.0"`` (exportação com
    ponto decimal), ``"1.234.567"`` (ponto como separador de milhar) e
    ``"1.234,0"`` (padrão brasileiro). Contagens não inteiras ou negativas geram
    erro, pois indicam leitura incorreta.
    """
    if pd.api.types.is_numeric_dtype(valores):
        numeros = pd.to_numeric(valores)
    else:
        texto = valores.astype("string").str.replace(" ", "", regex=False)
        texto = texto.mask(texto.isin(["", "-"]))
        milhar = texto.str.fullmatch(r"\d{1,3}(\.\d{3})+").fillna(False)
        virgula = texto.str.contains(",", regex=False).fillna(False)
        sem_ponto = texto.str.replace(".", "", regex=False)
        texto = texto.mask(milhar, sem_ponto).mask(virgula, sem_ponto.str.replace(",", ".", regex=False))
        try:
            numeros = pd.to_numeric(texto, errors="raise")
        except (ValueError, TypeError) as erro:
            raise ValueError(f"Contagem não numérica: {erro}") from None
    invalidos = numeros.notna() & (((numeros % 1) != 0) | (numeros < 0))
    if invalidos.any():
        raise ValueError(f"Contagens não inteiras ou negativas: {valores[invalidos].head(5).tolist()}")
    return numeros.round().astype("Int64")


def _limpar_texto(serie: pd.Series) -> pd.Series:
    serie = serie.astype("string").str.strip()
    return serie.mask(serie == "")


def _padronizar(bruto: pd.DataFrame, colunas: tuple[str, ...], obrigatoria: str) -> pd.DataFrame:
    """Renomeia, limpa e tipa as colunas; descarta linhas vazias, de total e sem ``obrigatoria``."""
    df = bruto.rename(columns=_mapear_colunas(list(bruto.columns)))[list(colunas)].copy()
    for col in colunas:
        if col not in ("qtd_veiculos", "ano_fabricacao"):
            df[col] = _limpar_texto(df[col])
    df["qtd_veiculos"] = para_inteiro(df["qtd_veiculos"])
    if "ano_fabricacao" in df:
        df["ano_fabricacao"] = pd.to_numeric(_limpar_texto(df["ano_fabricacao"]), errors="coerce").astype("Int64")
    df = df.dropna(how="all")
    eh_total = (df["uf"].fillna("").str.upper().str.startswith("TOTAL")
                | df["municipio"].fillna("").str.upper().eq("TOTAL"))
    return df[~eh_total & df[obrigatoria].notna()].reset_index(drop=True)


# --- leitores públicos -----------------------------------------------------------------

def ler_frota_combustivel(caminho: str | Path) -> pd.DataFrame:
    """Lê um arquivo de frota por município e combustível (colunas ``COLUNAS_COMBUSTIVEL``).

    Linhas de total e linhas totalmente vazias são descartadas; os rótulos de
    texto são preservados como publicados (apenas com espaços aparados).
    """
    caminho = Path(caminho)
    partes = [_padronizar(b, COLUNAS_COMBUSTIVEL, "combustivel")
              for b in _ler_blocos(caminho, COLUNAS_COMBUSTIVEL, None)]
    return pd.concat(partes, ignore_index=True)


def ler_frota_marca_modelo(caminho: str | Path, tamanho_bloco: int = 1_000_000) -> Iterator[pd.DataFrame]:
    """Lê o arquivo de frota por marca/modelo em blocos (colunas ``COLUNAS_MARCA_MODELO``).

    ``ano_fabricacao`` é inteiro anulável: rótulos como "Sem Informação" viram nulos.
    Linhas sem marca/modelo são mantidas (com ``marca_modelo`` nulo) para não
    perder veículos do total.
    """
    caminho = Path(caminho)
    for bloco in _ler_blocos(caminho, COLUNAS_MARCA_MODELO, tamanho_bloco):
        yield _padronizar(bloco, COLUNAS_MARCA_MODELO, "qtd_veiculos")
