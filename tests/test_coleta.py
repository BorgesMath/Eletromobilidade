import io
import zipfile

import pytest

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
    def __init__(self, conteudo: bytes, cabecalhos: dict):
        self.conteudo, self.headers = conteudo, cabecalhos

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for i in range(0, len(self.conteudo), chunk_size):
            yield self.conteudo[i:i + chunk_size]


class _Sessao:
    def __init__(self, conteudo: bytes, cabecalhos: dict | None = None):
        self.resposta = _Resposta(conteudo, cabecalhos or {"Content-Length": str(len(conteudo))})
        self.chamadas = 0

    def get(self, *args, **kwargs):
        self.chamadas += 1
        return self.resposta


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
    assert sessao.chamadas == 1


def test_baixar_rejeita_download_incompleto(tmp_path):
    conteudo = _zip_bytes()
    sessao = _Sessao(conteudo[:-10], {"Content-Length": str(len(conteudo))})
    with pytest.raises(IOError, match="incompleto"):
        baixar(LINK_ZIP, tmp_path, sessao)
    assert not any((tmp_path / "marca_modelo" / "2026").iterdir())


def test_baixar_rejeita_zip_invalido(tmp_path):
    with pytest.raises(IOError, match="zip válido"):
        baixar(LINK_ZIP, tmp_path, _Sessao(b"<html>erro</html>"))
