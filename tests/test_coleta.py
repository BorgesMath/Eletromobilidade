from eletromobilidade.coleta import Link, extrair_links, url_download

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


def test_url_download_remove_sufixos_plone():
    assert url_download("https://x/arq.xlsx/view") == "https://x/arq.xlsx"
    assert url_download("https://x/arq.xlsx/@@download/file") == "https://x/arq.xlsx"


def test_extrair_links():
    links = extrair_links(HTML, BASE)
    assert [l.tabela for l in links] == ["uf_tipo", "municipio_tipo", "combustivel", "marca_modelo"]
    comb = links[2]
    assert comb.url == ("https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/"
                        "D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx")
    assert comb.periodo == (2025, 1)
    assert comb.nome_arquivo == "D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2025.xlsx"
    assert links[1].periodo == (2025, 3)
    assert isinstance(comb, Link)
