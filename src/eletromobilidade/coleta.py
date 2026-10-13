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

import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .leitura import EXTENSOES_DADOS, identificar_tabela, inferir_periodo

log = logging.getLogger(__name__)

URL_PAGINA = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-{ano}"
URL_CKAN = "https://dados.transportes.gov.br/api/3/action/package_show"
DATASET_RENAVAM = "12686da0-3d71-4499-b432-d270f785c907"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; eletromobilidade/0.1)"}

FONTES = ("ckan", "portal")
TABELAS = ("marca_modelo", "combustivel", "municipio_tipo", "uf_tipo")


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
    sessao = sessao or requests.Session()
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


def listar_recursos_ckan(dataset: str = DATASET_RENAVAM, sessao: requests.Session | None = None) -> list[Link]:
    sessao = sessao or requests.Session()
    resposta = sessao.get(URL_CKAN, params={"id": dataset}, headers=CABECALHOS, timeout=60)
    resposta.raise_for_status()
    return extrair_recursos_ckan(resposta.json())


# --- seleção e download ----------------------------------------------------------------

def listar(anos: list[int], fontes: tuple[str, ...] = FONTES,
           sessao: requests.Session | None = None) -> list[Link]:
    """Links das fontes pedidas para os anos pedidos.

    Uma fonte indisponível gera aviso e é ignorada, para não impedir a coleta das demais.
    """
    sessao = sessao or requests.Session()
    links: list[Link] = []
    for fonte in fontes:
        try:
            if fonte == "ckan":
                links += [l for l in listar_recursos_ckan(sessao=sessao) if l.periodo and l.periodo[0] in anos]
            elif fonte == "portal":
                for ano in anos:
                    links += listar_links(ano, sessao)
            else:
                raise ValueError(f"Fonte desconhecida: {fonte}")
        except requests.RequestException as erro:
            log.warning("Fonte %s indisponível: %s", fonte, erro)
    return links


def selecionar(links: list[Link], tabela: str, meses: list[int] | None = None,
               fontes: tuple[str, ...] = FONTES) -> list[Link]:
    """Um link por período da tabela pedida; havendo o mesmo período em duas fontes,
    vale a que aparece primeiro em ``fontes``. Links sem período identificado são mantidos."""
    candidatos = [l for l in links if l.tabela == tabela and (not meses or (l.periodo and l.periodo[1] in meses))]
    candidatos.sort(key=lambda l: fontes.index(l.fonte) if l.fonte in fontes else len(fontes))
    escolhidos: dict[object, Link] = {}
    for link in candidatos:
        chave = link.periodo or link.url
        escolhidos.setdefault(chave, link)
    return sorted(escolhidos.values(), key=lambda l: (l.periodo or (0, 0), l.url))


def _verificar(arquivo: Path, nome_final: str, esperado: int | None) -> None:
    tamanho = arquivo.stat().st_size
    if esperado is not None and tamanho != esperado:
        raise IOError(f"Download incompleto de {nome_final}: {tamanho} de {esperado} bytes.")
    if nome_final.lower().endswith(".zip") and not zipfile.is_zipfile(arquivo):
        raise IOError(f"{nome_final} não é um zip válido.")


def baixar(link: Link, destino: str | Path, sessao: requests.Session | None = None,
           sobrescrever: bool = False) -> Path:
    """Baixa para ``destino/{tabela}/{ano}/``; reaproveita o arquivo se já existir.

    O arquivo é gravado como ``.parcial`` e só é renomeado depois de conferido o
    tamanho (``Content-Length``) e, para ``.zip``, a estrutura do arquivo.
    """
    sessao = sessao or requests.Session()
    pasta = Path(destino) / link.tabela / (str(link.periodo[0]) if link.periodo else "sem_periodo")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / link.nome_arquivo
    if caminho.exists() and not sobrescrever:
        log.info("Já existe: %s", caminho)
        return caminho
    temporario = caminho.with_name(caminho.name + ".parcial")
    try:
        with sessao.get(link.url, headers=CABECALHOS, stream=True, timeout=300) as resposta:
            resposta.raise_for_status()
            # Com compressão de transporte o Content-Length não corresponde aos bytes gravados.
            comprimido = resposta.headers.get("Content-Encoding", "identity") != "identity"
            esperado = None if comprimido else resposta.headers.get("Content-Length")
            with open(temporario, "wb") as f:
                for bloco in resposta.iter_content(chunk_size=1 << 20):
                    f.write(bloco)
        _verificar(temporario, caminho.name, int(esperado) if esperado else None)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    temporario.replace(caminho)
    log.info("Baixado: %s", caminho)
    return caminho


def baixar_tabela(tabela: str, anos: list[int], destino: str | Path, meses: list[int] | None = None,
                  fontes: tuple[str, ...] = FONTES, sobrescrever: bool = False) -> list[Path]:
    """Baixa os arquivos de uma tabela (ex.: ``"marca_modelo"``) para os anos/meses pedidos."""
    sessao = requests.Session()
    links = selecionar(listar(anos, fontes, sessao), tabela, meses, fontes)
    if not links:
        log.warning("Nenhum arquivo de %s encontrado para %s nas fontes %s.", tabela, anos, fontes)
    baixados = []
    for link in links:
        if link.periodo is None:
            log.warning("Período não identificado para %s; baixando mesmo assim.", link.url)
        baixados.append(baixar(link, destino, sessao, sobrescrever))
    return baixados
