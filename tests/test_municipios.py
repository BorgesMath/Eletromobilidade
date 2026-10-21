from pathlib import Path

import pandas as pd
import pytest

from eletromobilidade.municipios import (carregar_grafias, carregar_municipios, chave_municipio,
                                         codigos_municipio, dimensao_municipio, sem_codigo, tabela_ibge)
from eletromobilidade.ufs import UFS

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"
CABECALHO_GRAFIAS = "uf_sigla;municipio_senatran;cod_municipio_ibge;nota\n"


def test_chave_ignora_acento_caixa_e_pontuacao():
    assert chave_municipio("Pingo-d'Água") == chave_municipio("PINGO D'AGUA") == "PINGO D AGUA"
    assert chave_municipio("  Xique-Xique ") == "XIQUE XIQUE"


def test_instantaneo_do_ibge():
    municipios = carregar_municipios()
    assert len(municipios) == 5571
    assert set(municipios["uf_sigla"]) == {sigla for sigla, _, _ in UFS.values()}
    # o mais novo: instalado em 2025, e por isso fora do Censo 2022 e da malha municipal
    assert municipios.set_index("cod_municipio_ibge").loc[5101837, "municipio_ibge"] == "Boa Esperança do Norte"


def test_tabela_ibge_rejeita_resposta_incompleta():
    registro = {"municipio-id": 3550308, "UF-sigla": "SP", "municipio-nome": "São Paulo"}
    with pytest.raises(ValueError, match="devolveu 1 municípios"):
        tabela_ibge([registro])


def test_grafias_versionadas_carregam():
    grafias = carregar_grafias()
    assert len(grafias) == 41
    assert grafias["nota"].str.startswith("IBGE: ").all()


def test_codigos_por_nome_e_por_grafia():
    uf = pd.Series(["SP", "SP", "SP", "SC", "MG", None, "SP"])
    nome = pd.Series(["SAO PAULO", "EMBU", "EMBU DAS ARTES", "SAO LOURENCO D'OESTE", "BARAO D0 MONTE ALTO",
                      "SEM INFORMACAO", "CIDADE QUE NAO EXISTE"])
    codigos = codigos_municipio(uf, nome)
    assert str(codigos.dtype) == "Int64"
    assert codigos.iloc[:5].tolist() == [3550308, 3515004, 3515004, 4216909, 3105509]
    assert codigos.iloc[5:].isna().all()


def test_codigo_depende_da_uf():
    # "Bom Jesus" existe em cinco UFs; em Goiás o IBGE grafa "Bom Jesus de Goiás".
    codigos = codigos_municipio(pd.Series(["GO", "PI", "SC"]), pd.Series(["BOM JESUS"] * 3))
    assert codigos.tolist() == [5203500, 2201903, 4202537]


@pytest.mark.parametrize("linhas, erro", [
    ("SP;PARATI;3303807;código do RJ\n", "incompatível com a UF"),
    ("RJ;PARATI;3399999;não existe\n", "não estão no IBGE"),
    ("RJ;PARATY;3303807;já é o nome do IBGE\n", "já casam com o nome do IBGE"),
    ("RJ;PARATI;3303807;a\nRJ;PARATI;3303807;b\n", "repetidas"),
    ("RJ;PARATI;3303807;nota; com ponto e vírgula\n", "4 campos"),
])
def test_grafias_conferidas_contra_o_ibge(tmp_path, linhas, erro):
    caminho = tmp_path / "grafias.csv"
    caminho.write_text(CABECALHO_GRAFIAS + linhas, encoding="utf-8")
    with pytest.raises(ValueError, match=erro):
        carregar_grafias(caminho)


def _painel(linhas) -> pd.DataFrame:
    painel = pd.DataFrame(linhas, columns=["data_referencia", "uf_sigla", "municipio_norm", "frota_total"])
    painel["data_referencia"] = pd.to_datetime(painel["data_referencia"])
    painel["cod_uf_ibge"] = pd.array([35 if uf == "SP" else None for uf in painel["uf_sigla"]], dtype="Int64")
    painel["regiao"] = ["Sudeste" if uf == "SP" else None for uf in painel["uf_sigla"]]
    painel["cod_municipio_ibge"] = codigos_municipio(painel["uf_sigla"], painel["municipio_norm"])
    return painel


def test_dimensao_une_as_grafias_de_um_codigo():
    painel = _painel([
        ("2022-03-01", "SP", "EMBU", 10),
        ("2022-04-01", "SP", "EMBU DAS ARTES", 11),
        ("2022-04-01", "SP", "SAO PAULO", 100),
        ("2022-04-01", None, "SEM INFORMACAO", 5),
    ])
    dimensao = dimensao_municipio([painel]).set_index("municipio_norm")
    assert len(dimensao) == 3
    embu = dimensao.loc["EMBU DAS ARTES"]
    assert (embu["cod_municipio_ibge"], embu["municipio_ibge"]) == (3515004, "Embu das Artes")
    assert embu["grafias_senatran"] == "EMBU | EMBU DAS ARTES"
    assert dimensao.loc["SAO PAULO", "municipio_ibge"] == "São Paulo"
    assert pd.isna(dimensao.loc["SEM INFORMACAO", "cod_municipio_ibge"])
    assert pd.isna(dimensao.loc["SEM INFORMACAO", "municipio_ibge"])


def test_sem_codigo_lista_so_municipio_com_uf():
    painel = _painel([
        ("2026-09-01", "SP", "CIDADE QUE NAO EXISTE", 7),
        ("2026-09-01", "SP", "SAO PAULO", 100),
        ("2026-09-01", None, "SEM INFORMACAO", 5),
    ])
    faltando = sem_codigo(painel)
    assert faltando[["uf_sigla", "municipio_norm", "frota_total"]].values.tolist() == [
        ["SP", "CIDADE QUE NAO EXISTE", 7]]


# --- resultados publicados ----------------------------------------------------------------
#
# Estes testes leem resultados/, que é versionado. São os que falham quando um mês novo
# traz uma grafia que não está no IBGE nem em dados/municipios_grafias.csv, e quando a
# tabela de grafias muda sem que processar + publicar tenham rodado de novo.

TABELAS_MUNICIPAIS = ["combustivel_municipio", "combustivel_eletrificados", "modelo_municipio",
                      "modelo_eletrificados", "conciliacao_municipio"]


@pytest.mark.parametrize("tabela", TABELAS_MUNICIPAIS)
def test_resultados_todo_municipio_com_uf_tem_codigo(tabela):
    df = pd.read_parquet(RESULTADOS / f"{tabela}.parquet",
                         columns=["uf_sigla", "municipio_norm", "cod_municipio_ibge"]).drop_duplicates()
    faltando = df[df["uf_sigla"].notna() & df["cod_municipio_ibge"].isna()]
    assert faltando.empty, ("sem código IBGE; inclua em dados/municipios_grafias.csv: "
                            f"{faltando[['uf_sigla', 'municipio_norm']].values.tolist()[:20]}")


@pytest.mark.parametrize("tabela", TABELAS_MUNICIPAIS)
def test_resultados_codigo_igual_ao_das_tabelas_atuais(tabela):
    df = pd.read_parquet(RESULTADOS / f"{tabela}.parquet",
                         columns=["uf_sigla", "municipio_norm", "cod_municipio_ibge"]).drop_duplicates()
    atual = codigos_municipio(df["uf_sigla"], df["municipio_norm"])
    divergentes = df[atual.fillna(-1) != df["cod_municipio_ibge"].fillna(-1)]
    assert divergentes.empty, ("resultados/ defasado em relação a dados/municipios*.csv; rode processar e "
                               f"publicar: {divergentes.values.tolist()[:20]}")


def test_resultados_dimensao_cobre_os_fatos_com_um_codigo_por_linha():
    dimensao = pd.read_parquet(RESULTADOS / "municipios_dimensao.parquet")
    codigos = dimensao["cod_municipio_ibge"].dropna()
    assert codigos.is_unique
    assert dimensao.loc[dimensao["cod_municipio_ibge"].isna(), "uf_sigla"].isna().all()
    fato = pd.read_parquet(RESULTADOS / "combustivel_municipio.parquet", columns=["cod_municipio_ibge"])
    assert set(fato["cod_municipio_ibge"].dropna()) <= set(codigos)
