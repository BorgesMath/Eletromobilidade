"""Descoberta e download dos arquivos de frota no portal da SENATRAN (gov.br).

Cada ano tem uma página ``frota-de-veiculos-{ano}`` com links mensais. Os nomes
dos arquivos não seguem padrão estável (há prefixos ``copy_of_``, grafias como
``Maro`` para "Março" etc.), por isso a tabela e o período são inferidos do
link e do texto âncora, e não de um nome fixo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .leitura import EXTENSOES_DADOS, inferir_periodo
from .texto import normalizar

log = logging.getLogger(__name__)

URL_PAGINA = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-{ano}"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; eletromobilidade/0.1)"}


@dataclass(frozen=True)
class Link:
    url: str
    texto: str
    tabela: str
    periodo: tuple[int, int] | None

    @property
    def nome_arquivo(self) -> str:
        return Path(unquote(urlparse(self.url).path)).name


def url_download(href: str) -> str:
    """Remove sufixos de visualização do Plone (``/view``, ``/@@download/file``)."""
    for sufixo in ("/view", "/@@download/file", "/@@download"):
        if href.endswith(sufixo):
            return href[: -len(sufixo)]
    return href


def classificar_tabela(texto: str) -> str:
    t = normalizar(texto).replace("_", " ")
    if "COMBUSTIVEL" in t:
        return "combustivel"
    if "MARCA" in t or "MODELO" in t:
        return "marca_modelo"
    if "TIPO" in t:
        return "municipio_tipo" if "MUNICIPIO" in t else "uf_tipo"
    return "outro"


def extrair_links(html: str, url_base: str) -> list[Link]:
    """Lista os links para arquivos de dados presentes no HTML da página de um ano."""
    sopa = BeautifulSoup(html, "html.parser")
    vistos: set[str] = set()
    links: list[Link] = []
    for a in sopa.find_all("a", href=True):
        url = url_download(urljoin(url_base, a["href"].strip()))
        if not urlparse(url).path.lower().endswith(EXTENSOES_DADOS) or url in vistos:
            continue
        vistos.add(url)
        texto = a.get_text(" ", strip=True)
        nome = Path(unquote(urlparse(url).path)).name
        links.append(Link(
            url=url,
            texto=texto,
            tabela=classificar_tabela(f"{nome} {texto}"),
            periodo=inferir_periodo(nome) or inferir_periodo(texto),
        ))
    return links


def listar_links(ano: int, sessao: requests.Session | None = None) -> list[Link]:
    sessao = sessao or requests.Session()
    url = URL_PAGINA.format(ano=ano)
    resposta = sessao.get(url, headers=CABECALHOS, timeout=60)
    resposta.raise_for_status()
    return extrair_links(resposta.text, url)


def baixar(link: Link, destino: str | Path, sessao: requests.Session | None = None,
           sobrescrever: bool = False) -> Path:
    """Baixa o arquivo para ``destino/AAAA/``; reaproveita o arquivo se já existir."""
    sessao = sessao or requests.Session()
    pasta = Path(destino) / (str(link.periodo[0]) if link.periodo else "sem_periodo")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / link.nome_arquivo
    if caminho.exists() and not sobrescrever:
        log.info("Já existe: %s", caminho)
        return caminho
    temporario = caminho.with_suffix(caminho.suffix + ".parcial")
    with sessao.get(link.url, headers=CABECALHOS, stream=True, timeout=300) as resposta:
        resposta.raise_for_status()
        with open(temporario, "wb") as f:
            for bloco in resposta.iter_content(chunk_size=1 << 20):
                f.write(bloco)
    temporario.replace(caminho)
    log.info("Baixado: %s", caminho)
    return caminho


def baixar_frota_combustivel(anos: list[int], destino: str | Path,
                             meses: list[int] | None = None) -> list[Path]:
    """Baixa os arquivos "Frota por UF, Município e Combustível" dos anos/meses pedidos."""
    sessao = requests.Session()
    baixados: list[Path] = []
    for ano in anos:
        links = [l for l in listar_links(ano, sessao) if l.tabela == "combustivel"]
        if meses:
            links = [l for l in links if l.periodo and l.periodo[1] in meses]
        if not links:
            log.warning("Nenhum arquivo de combustível encontrado para %s.", ano)
        for link in links:
            if link.periodo is None:
                log.warning("Período não identificado para %s; baixando mesmo assim.", link.url)
            baixados.append(baixar(link, destino, sessao))
    return baixados
