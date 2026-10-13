"""Descoberta e download dos arquivos de frota da SENATRAN.

Duas fontes:

* ``ckan``: portal de dados abertos do Ministério dos Transportes
  (dados.transportes.gov.br), conjunto RENAVAM. Os recursos são listados pela API
  CKAN (``package_show``), o que dá URLs estáveis. Contém, entre outros, o arquivo
  mensal "Frota por UF, Município, Marca e Modelo, Ano" (``.zip``).
* ``portal``: páginas anuais ``frota-de-veiculos-{ano}`` do gov.br, raspadas do
  HTML. Contêm as tabelas por tipo de veículo e por combustível.

Os nomes dos arquivos não seguem padrão estável (prefixos ``copy_of_``, ``Maro``
para "Março" etc.), por isso a tabela e o período são inferidos do nome e do
título de cada recurso.
"""

from __future__ import annotations

import json
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .leitura import EXTENSOES_DADOS, identificar_tabela, inferir_periodo

log = logging.getLogger(__name__)

URL_PAGINA = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-{ano}"
URL_CKAN = "https://dados.transportes.gov.br/api/3/action/package_show"
DATASET_RENAVAM = "12686da0-3d71-4499-b432-d270f785c907"
ARQUIVO_CACHE_CKAN = "ckan_renavam.json"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; eletromobilidade/0.1)"}

FONTES = ("ckan", "portal")
TABELAS = ("marca_modelo", "combustivel", "municipio_tipo", "uf_tipo", "ano_fabricacao", "tipo_especie_eixos",
           "restricao", "potencia", "cep", "cor")


def criar_sessao(tentativas: int = 5, espera: float = 2.0) -> requests.Session:
    """Sessão HTTP com novas tentativas e espera exponencial (2, 4, 8, 16 s...).

    Os servidores do gov.br respondem de forma intermitente com 502/503/504 e
    estouros de tempo; essas falhas são repetidas, as demais não.
    """
    sessao = requests.Session()
    retry = Retry(total=tentativas, connect=tentativas, read=tentativas, status=tentativas,
                  backoff_factor=espera, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET", "HEAD"), raise_on_status=False)
    adaptador = HTTPAdapter(max_retries=retry)
    sessao.mount("https://", adaptador)
    sessao.mount("http://", adaptador)
    sessao.headers.update(CABECALHOS)
    return sessao


@dataclass(frozen=True)
class Link:
    url: str
    texto: str
    tabela: str
    periodo: tuple[int, int] | None
    fonte: str = "portal"

    @property
    def nome_arquivo(self) -> str:
        return Path(unquote(urlparse(self.url).path)).name


def _criar_link(url: str, texto: str, fonte: str) -> Link | None:
    """Monta um ``Link`` se a URL apontar para um arquivo de dados."""
    nome = Path(unquote(urlparse(url).path)).name
    if not nome.lower().endswith(EXTENSOES_DADOS):
        return None
    return Link(
        url=url,
        texto=texto,
        tabela=identificar_tabela(f"{nome} {texto}"),
        periodo=inferir_periodo(nome) or inferir_periodo(texto),
        fonte=fonte,
    )


def url_download(href: str) -> str:
    """Remove sufixos de visualização do Plone (``/view``, ``/@@download/file``)."""
    for sufixo in ("/view", "/@@download/file", "/@@download"):
        if href.endswith(sufixo):
            return href[: -len(sufixo)]
    return href


# --- fonte "portal" (HTML do gov.br) -------------------------------------------------

def extrair_links(html: str, url_base: str) -> list[Link]:
    """Lista os links para arquivos de dados presentes no HTML da página de um ano."""
    sopa = BeautifulSoup(html, "html.parser")
    vistos: set[str] = set()
    links: list[Link] = []
    for a in sopa.find_all("a", href=True):
        url = url_download(urljoin(url_base, a["href"].strip()))
        if url in vistos:
            continue
        link = _criar_link(url, a.get_text(" ", strip=True), "portal")
        if link:
            vistos.add(url)
            links.append(link)
    return links


def listar_links(ano: int, sessao: requests.Session | None = None) -> list[Link]:
    sessao = sessao or criar_sessao()
    url = URL_PAGINA.format(ano=ano)
    resposta = sessao.get(url, headers=CABECALHOS, timeout=60)
    resposta.raise_for_status()
    return extrair_links(resposta.text, url)


# --- fonte "ckan" (API do portal de dados abertos) -----------------------------------

def extrair_recursos_ckan(resposta: dict) -> list[Link]:
    """Converte a resposta de ``package_show`` em ``Link``s, ignorando recursos que não são arquivos."""
    if not resposta.get("success"):
        raise ValueError(f"API CKAN retornou erro: {resposta.get('error')}")
    links: list[Link] = []
    for recurso in resposta["result"].get("resources", []):
        url = (recurso.get("url") or "").strip()
        link = _criar_link(url, recurso.get("name") or "", "ckan") if url else None
        if link:
            links.append(link)
    return links


def listar_recursos_ckan(dataset: str = DATASET_RENAVAM, sessao: requests.Session | None = None,
                         cache: Path | None = None) -> list[Link]:
    """Recursos do conjunto no CKAN.

    Com ``cache``, a resposta da API é guardada em disco e reaproveitada quando a API
    estiver fora do ar (o ``package_show`` do portal responde 503 com frequência,
    enquanto os links de download continuam funcionando).
    """
    sessao = sessao or criar_sessao()
    try:
        resposta = sessao.get(URL_CKAN, params={"id": dataset}, headers=CABECALHOS, timeout=60)
        resposta.raise_for_status()
        conteudo = resposta.json()
    except requests.RequestException as erro:
        if cache is None or not Path(cache).exists():
            raise
        log.warning("API CKAN indisponível (%s); usando a listagem guardada em %s.", erro, cache)
        return extrair_recursos_ckan(json.loads(Path(cache).read_text(encoding="utf-8")))
    links = extrair_recursos_ckan(conteudo)
    if cache is not None:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return links


# --- seleção e download ----------------------------------------------------------------

def listar(anos: list[int], fontes: tuple[str, ...] = FONTES,
           sessao: requests.Session | None = None, cache_ckan: Path | None = None) -> list[Link]:
    """Links das fontes pedidas para os anos pedidos.

    Uma fonte indisponível gera aviso e é ignorada, para não impedir a coleta das demais.
    """
    sessao = sessao or criar_sessao()
    links: list[Link] = []
    for fonte in fontes:
        try:
            if fonte == "ckan":
                links += [l for l in listar_recursos_ckan(sessao=sessao, cache=cache_ckan)
                          if l.periodo and l.periodo[0] in anos]
            elif fonte == "portal":
                for ano in anos:
                    links += listar_links(ano, sessao)
            else:
                raise ValueError(f"Fonte desconhecida: {fonte}")
        except requests.RequestException as erro:
            log.warning("Fonte %s indisponível: %s", fonte, erro)
    return links


def candidatos_por_periodo(links: list[Link], tabela: str, meses: list[int] | None = None,
                           fontes: tuple[str, ...] = FONTES) -> dict[object, list[Link]]:
    """Links da tabela agrupados por período, cada grupo em ordem de preferência de fonte.

    Links sem período identificado formam grupos próprios (chave = URL).
    """
    candidatos = [l for l in links if l.tabela == tabela and (not meses or (l.periodo and l.periodo[1] in meses))]
    candidatos.sort(key=lambda l: fontes.index(l.fonte) if l.fonte in fontes else len(fontes))
    grupos: dict[object, list[Link]] = {}
    for link in candidatos:
        grupos.setdefault(link.periodo or link.url, []).append(link)
    return dict(sorted(grupos.items(), key=lambda kv: (kv[1][0].periodo or (0, 0), kv[1][0].url)))


def selecionar(links: list[Link], tabela: str, meses: list[int] | None = None,
               fontes: tuple[str, ...] = FONTES) -> list[Link]:
    """Um link por período da tabela pedida; havendo o mesmo período em duas fontes,
    vale a que aparece primeiro em ``fontes``. Links sem período identificado são mantidos."""
    return [grupo[0] for grupo in candidatos_por_periodo(links, tabela, meses, fontes).values()]


def _verificar(arquivo: Path, nome_final: str, esperado: int | None) -> None:
    tamanho = arquivo.stat().st_size
    if esperado is not None and tamanho != esperado:
        raise IOError(f"Download incompleto de {nome_final}: {tamanho} de {esperado} bytes.")
    if nome_final.lower().endswith(".zip") and not zipfile.is_zipfile(arquivo):
        raise IOError(f"{nome_final} não é um zip válido.")


def _tamanho_total(resposta, ja_baixado: int) -> int | None:
    """Tamanho final esperado do arquivo, a partir de Content-Range (206) ou Content-Length (200)."""
    faixa = resposta.headers.get("Content-Range", "")
    if resposta.status_code == 206 and "/" in faixa and not faixa.endswith("/*"):
        return int(faixa.rsplit("/", 1)[1])
    # Com compressão de transporte o Content-Length não corresponde aos bytes gravados.
    if resposta.headers.get("Content-Encoding", "identity") != "identity":
        return None
    tamanho = resposta.headers.get("Content-Length")
    return int(tamanho) + ja_baixado if tamanho else None


def baixar(link: Link, destino: str | Path, sessao: requests.Session | None = None,
           sobrescrever: bool = False, tentativas: int = 5, espera: float = 2.0) -> Path:
    """Baixa para ``destino/{tabela}/{ano}/``; reaproveita o arquivo se já existir.

    O arquivo é gravado como ``.parcial``. Se a conexão cair no meio, o download é
    retomado do ponto em que parou (cabeçalho ``Range``), com espera exponencial,
    até ``tentativas`` vezes. Só depois de conferido o tamanho e, para ``.zip``, a
    estrutura do arquivo, o ``.parcial`` é renomeado.
    """
    sessao = sessao or criar_sessao()
    pasta = Path(destino) / link.tabela / (str(link.periodo[0]) if link.periodo else "sem_periodo")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / link.nome_arquivo
    if caminho.exists() and not sobrescrever:
        log.info("Já existe: %s", caminho)
        return caminho
    temporario = caminho.with_name(caminho.name + ".parcial")
    temporario.unlink(missing_ok=True)
    esperado = None
    try:
        for tentativa in range(tentativas + 1):
            ja_baixado = temporario.stat().st_size if temporario.exists() else 0
            cabecalhos = {"Range": f"bytes={ja_baixado}-"} if ja_baixado else {}
            try:
                with sessao.get(link.url, headers=cabecalhos, stream=True, timeout=300) as resposta:
                    resposta.raise_for_status()
                    if ja_baixado and resposta.status_code != 206:
                        ja_baixado = 0  # servidor ignorou o Range: recomeça do zero
                    esperado = _tamanho_total(resposta, ja_baixado) or esperado
                    with open(temporario, "ab" if ja_baixado else "wb") as f:
                        for bloco in resposta.iter_content(chunk_size=1 << 20):
                            f.write(bloco)
                break
            except (requests.ConnectionError, requests.Timeout,
                    requests.exceptions.ChunkedEncodingError) as erro:
                if tentativa == tentativas:
                    raise
                pausa = espera * 2 ** tentativa
                log.warning("%s: conexão interrompida com %d bytes (%s); retomando em %.0f s.",
                            link.nome_arquivo, temporario.stat().st_size if temporario.exists() else 0,
                            type(erro).__name__, pausa)
                time.sleep(pausa)
        _verificar(temporario, caminho.name, esperado)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    temporario.replace(caminho)
    log.info("Baixado: %s", caminho)
    return caminho


FALHAS_PARA_DESISTIR = 3


@dataclass
class ResultadoDownload:
    baixados: list[Path]
    falhas: list[tuple[Link, str]]


def baixar_tabela(tabela: str, anos: list[int], destino: str | Path, meses: list[int] | None = None,
                  fontes: tuple[str, ...] = FONTES, sobrescrever: bool = False) -> ResultadoDownload:
    """Baixa os arquivos de uma tabela (ex.: ``"marca_modelo"``) para os anos/meses pedidos.

    Para cada período tenta as fontes em ordem de preferência. Um período que falha
    em todas não interrompe os demais: a falha é registrada e informada no fim.
    """
    sessao = criar_sessao()
    grupos = candidatos_por_periodo(listar(anos, fontes, sessao, Path(destino) / ARQUIVO_CACHE_CKAN),
                                    tabela, meses, fontes)
    if not grupos:
        log.warning("Nenhum arquivo de %s encontrado para %s nas fontes %s.", tabela, anos, fontes)
    resultado = ResultadoDownload([], [])
    falhas_seguidas: dict[str, int] = {}
    for grupo in grupos.values():
        if grupo[0].periodo is None:
            log.warning("Período não identificado para %s; baixando mesmo assim.", grupo[0].url)
        erro_final = "nenhuma fonte disponível"
        for link in grupo:
            if falhas_seguidas.get(link.fonte, 0) >= FALHAS_PARA_DESISTIR:
                erro_final = f"fonte {link.fonte} fora do ar nesta execução"
                continue
            try:
                resultado.baixados.append(baixar(link, destino, sessao, sobrescrever))
                falhas_seguidas[link.fonte] = 0
                break
            except (requests.RequestException, OSError) as erro:
                log.warning("Falha em %s (%s): %s", link.nome_arquivo, link.fonte, erro)
                falhas_seguidas[link.fonte] = falhas_seguidas.get(link.fonte, 0) + 1
                erro_final = str(erro)
                if falhas_seguidas[link.fonte] == FALHAS_PARA_DESISTIR:
                    log.error("Fonte %s: %d falhas seguidas; demais arquivos dela ficam para outra execução.",
                              link.fonte, FALHAS_PARA_DESISTIR)
        else:
            resultado.falhas.append((grupo[-1], erro_final))
    if resultado.falhas:
        log.error("%d arquivo(s) não baixado(s): %s", len(resultado.falhas),
                  ", ".join(l.nome_arquivo for l, _ in resultado.falhas))
    return resultado
