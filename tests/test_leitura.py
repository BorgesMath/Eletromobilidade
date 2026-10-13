import zipfile

import pandas as pd
import pytest

from eletromobilidade.leitura import inferir_periodo, ler_frota_combustivel, ler_frota_marca_modelo, para_inteiro

from conftest import LINHAS_JAN, escrever_xlsx


@pytest.mark.parametrize("nome, esperado", [
    ("D_Frota_por_UF_Municipio_COMBUSTIVEL_Julho_2026.xlsx", (2026, 7)),
    ("copy_of_D_Frota_por_UF_Municipio_COMBUSTIVEL_Maro_2025.xlsx", (2025, 3)),
    ("Frota por UF, Município e Combustível - Março 2025", (2025, 3)),
    ("frota_combustivel_2024-11.csv", (2024, 11)),
    ("d_frota_por_uf_municipio_combustivel_janeito_2019.xlsx", (2019, 1)),
    ("frota_combustivel.xlsx", None),
    ("Janeiro_2025_e_Fevereiro_2025.xlsx", None),
])
def test_inferir_periodo(nome, esperado):
    assert inferir_periodo(nome) == esperado


def test_le_xlsx_com_cabecalho_na_primeira_linha(xlsx_jan):
    df = ler_frota_combustivel(xlsx_jan)
    assert list(df.columns) == ["uf", "municipio", "combustivel", "qtd_veiculos"]
    assert len(df) == len(LINHAS_JAN)
    assert df["qtd_veiculos"].dtype == "Int64"
    assert df["qtd_veiculos"].sum() == sum(l[3] for l in LINHAS_JAN)
    assert df.loc[0, "uf"] == "SAO PAULO"


def test_le_xlsx_com_titulo_e_linha_de_total(tmp_path):
    arq = escrever_xlsx(tmp_path / "combustivel_Janeiro_2026.xlsx", LINHAS_JAN,
                        titulo=["FROTA POR UF, MUNICÍPIO E COMBUSTÍVEL", "JANEIRO/2026"], total=True)
    df = ler_frota_combustivel(arq)
    assert len(df) == len(LINHAS_JAN)
    assert df["qtd_veiculos"].sum() == sum(l[3] for l in LINHAS_JAN)


def test_le_csv_latin1_ponto_e_virgula(tmp_path):
    texto = "UF;Município;Combustível Veículo;Qtd. Veículos\nACRE;ACRELANDIA;GASOLINA; 7.0\nACRE;ACRELANDIA;ELETRICO/FONTE EXTERNA;1.234\n"
    arq = tmp_path / "combustivel_2026-01.csv"
    arq.write_bytes(texto.encode("latin-1"))
    df = ler_frota_combustivel(arq)
    assert df["municipio"].tolist() == ["ACRELANDIA", "ACRELANDIA"]
    assert df["qtd_veiculos"].tolist() == [7, 1234]


def test_le_zip_com_xlsx(tmp_path, xlsx_jan):
    arq = tmp_path / "combustivel_Janeiro_2026.zip"
    with zipfile.ZipFile(arq, "w") as z:
        z.write(xlsx_jan, xlsx_jan.name)
    assert len(ler_frota_combustivel(arq)) == len(LINHAS_JAN)


def test_arquivo_sem_colunas_esperadas_falha(tmp_path):
    arq = tmp_path / "x.xlsx"
    pd.DataFrame({"A": [1], "B": [2]}).to_excel(arq, index=False)
    with pytest.raises(ValueError, match="Cabeçalho não encontrado"):
        ler_frota_combustivel(arq)


def test_para_inteiro():
    s = pd.Series([3, 4.0, " 7.0", "1.234.567", "12", None, ""], dtype=object)
    assert para_inteiro(s).tolist() == [3, 4, 7, 1234567, 12, pd.NA, pd.NA]


@pytest.mark.parametrize("valor", ["2.5", -1])
def test_para_inteiro_rejeita_contagens_invalidas(valor):
    with pytest.raises(ValueError):
        para_inteiro(pd.Series([valor], dtype=object))


def test_le_marca_modelo_em_blocos(zip_marca_modelo_jan):
    from conftest import LINHAS_MARCA_MODELO_JAN

    blocos = list(ler_frota_marca_modelo(zip_marca_modelo_jan, tamanho_bloco=5))
    assert len(blocos) == 3
    df = pd.concat(blocos, ignore_index=True)
    assert list(df.columns) == ["uf", "municipio", "marca_modelo", "ano_fabricacao", "qtd_veiculos"]
    assert df["qtd_veiculos"].sum() == sum(l[4] for l in LINHAS_MARCA_MODELO_JAN)
    assert df["ano_fabricacao"].dtype == "Int64"
    assert df["ano_fabricacao"].isna().sum() == 1  # "Sem Informação"
    assert df.loc[0, "marca_modelo"] == "I/BYD DOLPHIN GS 180EV"


@pytest.mark.parametrize("nome, tabela, periodo", [
    # nomes reais do portal (outubro/2026)
    ("D_Frota_por_UF_Municipio_COMBUSTIVEL_Setembro_2026.xlsx", "combustivel", (2026, 9)),
    ("i_frota_por_uf_municipio_marca_e_modelo_ano_setembro_2026.zip", "marca_modelo", (2026, 9)),
    ("F_Frota_por_UF_Municipio_ANO_FAB_MOD_Setembro_2026.xlsx", "ano_fabricacao", (2026, 9)),
    ("G_Frota_por_UF_Municipio_TIPO_ESPECIE_EIXOS_Julho_2026.xlsx", "tipo_especie_eixos", (2026, 7)),
    ("H_Frota_por_UF_Municipio_RESTRICAO_Julho_2026.xlsx", "restricao", (2026, 7)),
    ("E_Frota_por_UF_Municipio_POTENCIA_Julho_2026.xlsx", "potencia", (2026, 7)),
    ("A_Frota_por_UF_Municipio_CEP_Julho_2026.xlsx", "cep", (2026, 7)),
    ("C_Frota_por_UF_Municipio_COR_Julho_2026.xlsx", "cor", (2026, 7)),
    ("Frota_por_municipio_e_tipo_Junho_2026.xlsx", "municipio_tipo", (2026, 6)),
    ("Frota_por_uf_e_tipo_de_veiculo_Junho_2026.xlsx", "uf_tipo", (2026, 6)),
    ("frotapormunicipioetipofevereiro2026.xlsx", "municipio_tipo", (2026, 2)),
    ("frotaporufetipodeveiculofevereiro2026.xlsx", "uf_tipo", (2026, 2)),
])
def test_identificar_tabela_e_periodo_nomes_reais(nome, tabela, periodo):
    from eletromobilidade.leitura import identificar_tabela

    assert identificar_tabela(nome) == tabela
    assert inferir_periodo(nome) == periodo


def test_le_xlsx_com_acentos_corrompidos_e_linha_column(tmp_path):
    """Leiaute de d_frota_por_uf_municipio_combustivel_agosto_2019.xlsx."""
    linhas = [["Column1", "Column2", "Column3", "Column4"],
              ["UF", "MunicÃ­pio", "CombustÃ­vel VeÃ­culo", "Qtd. VeÃ­culos"],
              ["ACRE", "ACRELANDIA", "ALCOOL", 57],
              ["ACRE", "ACRELANDIA", "Sem InformaÃ§Ã£o", 95]]
    arq = tmp_path / "d_frota_por_uf_municipio_combustivel_agosto_2019.xlsx"
    pd.DataFrame(linhas).to_excel(arq, header=False, index=False)
    df = ler_frota_combustivel(arq)
    assert df["combustivel"].tolist() == ["ALCOOL", "Sem Informação"]
    assert df["qtd_veiculos"].sum() == 152
