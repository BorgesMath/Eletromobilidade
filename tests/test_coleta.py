import io
import zipfile

import pytest
import requests

from eletromobilidade.coleta import (Link, baixar, extrair_links, extrair_recursos_ckan, selecionar,
                                     url_download)

BASE = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2025"

# Trecho no formato das páginas Plone do gov.br (links relativos e absolutos, sufixo /view).
HTML = """
<div id="parent-fieldname-text">
  <h3>Janeiro</h3>
  <a href="copy_of_Frota_por_UF_e_Tipo_de_Veiculo_Janeiro_2025.xlsx">Frota por UF e Tipo de Veículo</a>
  <a href="https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/copy2_of_Frota_por_municipio_tipo_Maro_2025.xlsx/view">Frota por Município e Tipo</a>
  <a href="D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx/view">Frota por UF, Município e Combustível</a>
  <a href="D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx">duplicado</a>
  <a href="I_Frota_por_UF_Municipio_Marca_e_Modelo_Ano_Dezembro_2025.zip">Marca e Modelo</a>
  <a href="https://www.gov.br/transportes/pt-br">Início</a>
</div>
"""

CKAN_RECURSO = ("https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907/resource/"
                "{id}/download/{nome}")

# Estrutura padrão da resposta de package_show do CKAN.
CKAN = {
    "success": True,
    "result": {
        "id": "12686da0-3d71-4499-b432-d270f785c907",
        "resources": [
            {"id": "4408da67", "name": "Frota por UF, Município, Marca e Modelo, Ano - Setembro 2026",
             "format": "ZIP",
             "url": CKAN_RECURSO.format(id="4408da67", nome="i_frota_por_uf_municipio_marca_e_modelo_ano_setembro_2026.zip")},
            {"id": "aaaa0001", "name": "Frota por UF, Município, Marca e Modelo, Ano - Agosto 2026",
             "format": "ZIP",
             "url": CKAN_RECURSO.format(id="aaaa0001", nome="i_frota_por_uf_municipio_marca_e_modelo_ano_agosto_2026.zip")},
            {"id": "aaaa0002", "name": "Dicionário de dados", "format": "PDF",
             "url": CKAN_RECURSO.format(id="aaaa0002", nome="dicionario.pdf")},
            {"id": "aaaa0003", "name": "Sem URL", "format": "ZIP", "url": ""},
        ],
    },
}


def test_url_download_remove_sufixos_plone():
    assert url_download("https://x/arq.xlsx/view") == "https://x/arq.xlsx"
    assert url_download("https://x/arq.xlsx/@@download/file") == "https://x/arq.xlsx"


def test_extrair_links_portal():
    links = extrair_links(HTML, BASE)
    assert [l.tabela for l in links] == ["uf_tipo", "municipio_tipo", "combustivel", "marca_modelo"]
    comb = links[2]
    assert comb.url == ("https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/"
                        "D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx")
    assert comb.periodo == (2025, 1)
    assert comb.fonte == "portal"
    assert comb.nome_arquivo == "D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx"
    assert links[1].periodo == (2025, 3)


def test_extrair_recursos_ckan():
    links = extrair_recursos_ckan(CKAN)
    assert [(l.tabela, l.periodo, l.fonte) for l in links] == [
        ("marca_modelo", (2026, 9), "ckan"),
        ("marca_modelo", (2026, 8), "ckan"),
    ]
    assert links[0].nome_arquivo == "i_frota_por_uf_municipio_marca_e_modelo_ano_setembro_2026.zip"


def test_extrair_recursos_ckan_erro():
    with pytest.raises(ValueError, match="erro"):
        extrair_recursos_ckan({"success": False, "error": {"message": "Not found"}})


def test_selecionar_prefere_fonte_e_filtra_mes():
    ckan = Link("https://a/marca_setembro_2026.zip", "", "marca_modelo", (2026, 9), "ckan")
    portal = Link("https://b/Marca_Setembro_2026.zip", "", "marca_modelo", (2026, 9), "portal")
    outro_mes = Link("https://a/marca_agosto_2026.zip", "", "marca_modelo", (2026, 8), "ckan")
    comb = Link("https://b/combustivel_setembro_2026.xlsx", "", "combustivel", (2026, 9), "portal")
    links = [portal, ckan, outro_mes, comb]

    assert selecionar(links, "marca_modelo", fontes=("ckan", "portal")) == [outro_mes, ckan]
    assert selecionar(links, "marca_modelo", fontes=("portal", "ckan")) == [outro_mes, portal]
    assert selecionar(links, "marca_modelo", meses=[9]) == [ckan]
    assert selecionar(links, "combustivel") == [comb]


class _Resposta:
    def __init__(self, conteudo: bytes, cabecalhos: dict, status: int = 200, cair_apos: int | None = None):
        self.conteudo, self.headers, self.status_code, self.cair_apos = conteudo, cabecalhos, status, cair_apos

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        passo = 10_000  # blocos pequenos para simular quedas no meio do arquivo
        for i in range(0, len(self.conteudo), passo):
            if self.cair_apos is not None and i >= self.cair_apos:
                raise requests.exceptions.ChunkedEncodingError("conexão caiu")
            yield self.conteudo[i:i + passo]


class _Sessao:
    """Servidor falso: entrega ``conteudo``, opcionalmente caindo após ``cair_apos`` bytes
    nas ``quedas`` primeiras requisições, e atende ``Range`` se ``aceita_range``."""

    def __init__(self, conteudo: bytes, cabecalhos: dict | None = None, quedas: int = 0,
                 cair_apos: int | None = None, aceita_range: bool = True):
        self.conteudo, self.cabecalhos = conteudo, cabecalhos
        self.quedas, self.cair_apos, self.aceita_range = quedas, cair_apos, aceita_range
        self.pedidos: list[dict] = []

    def get(self, url, headers=None, **kwargs):
        headers = headers or {}
        self.pedidos.append(headers)
        cair = self.cair_apos if len(self.pedidos) <= self.quedas else None
        inicio = int(headers["Range"].split("=")[1].rstrip("-")) if "Range" in headers else 0
        if inicio and self.aceita_range:
            parte = self.conteudo[inicio:]
            return _Resposta(parte, {"Content-Length": str(len(parte)),
                                     "Content-Range": f"bytes {inicio}-{len(self.conteudo) - 1}/{len(self.conteudo)}"},
                             206, cair)
        cab = self.cabecalhos or {"Content-Length": str(len(self.conteudo))}
        return _Resposta(self.conteudo, cab, 200, cair)


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("frota.csv", "UF;Município;Marca Modelo;Ano Fabricação Veículo CRV;Qtd. Veículos\n")
    return buf.getvalue()


LINK_ZIP = Link("https://x/i_frota_por_uf_municipio_marca_e_modelo_ano_setembro_2026.zip", "",
                "marca_modelo", (2026, 9), "ckan")


def test_baixar_grava_por_tabela_e_ano_e_reaproveita(tmp_path):
    sessao = _Sessao(_zip_bytes())
    caminho = baixar(LINK_ZIP, tmp_path, sessao)
    assert caminho == tmp_path / "marca_modelo" / "2026" / LINK_ZIP.nome_arquivo
    assert zipfile.is_zipfile(caminho)
    assert baixar(LINK_ZIP, tmp_path, sessao) == caminho
    assert len(sessao.pedidos) == 1


def test_baixar_rejeita_download_incompleto(tmp_path):
    conteudo = _zip_bytes()
    sessao = _Sessao(conteudo[:-10], {"Content-Length": str(len(conteudo))})
    with pytest.raises(IOError, match="incompleto"):
        baixar(LINK_ZIP, tmp_path, sessao)
    assert not any((tmp_path / "marca_modelo" / "2026").iterdir())


def test_baixar_rejeita_zip_invalido(tmp_path):
    with pytest.raises(IOError, match="zip válido"):
        baixar(LINK_ZIP, tmp_path, _Sessao(b"<html>erro</html>"))


def _zip_grande() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("frota.csv", "UF;Município\n" + "SAO PAULO;SAO PAULO\n" * 5000)
    return buf.getvalue()


def test_baixar_retoma_de_onde_parou(tmp_path):
    conteudo = _zip_grande()
    sessao = _Sessao(conteudo, quedas=2, cair_apos=20_000)
    caminho = baixar(LINK_ZIP, tmp_path, sessao, espera=0, tentativas=3)
    assert caminho.read_bytes() == conteudo
    assert [p.get("Range") for p in sessao.pedidos] == [None, "bytes=20000-", "bytes=40000-"]


def test_baixar_recomeca_se_servidor_ignora_range(tmp_path):
    conteudo = _zip_grande()
    sessao = _Sessao(conteudo, quedas=1, cair_apos=20_000, aceita_range=False)
    assert baixar(LINK_ZIP, tmp_path, sessao, espera=0).read_bytes() == conteudo


def test_baixar_desiste_apos_tentativas(tmp_path):
    sessao = _Sessao(_zip_grande(), quedas=10, cair_apos=0)
    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        baixar(LINK_ZIP, tmp_path, sessao, espera=0, tentativas=2)
    assert len(sessao.pedidos) == 3
    assert not any((tmp_path / "marca_modelo" / "2026").iterdir())
