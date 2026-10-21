from pathlib import Path

import pandas as pd
import pytest

from eletromobilidade import pipeline
from eletromobilidade.populacao import (ano_da_estimativa, carregar_populacao, populacao_municipal,
                                        tabela_estimativas)

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"
PUBLICADOS = {2020, 2021, 2024, 2025, 2026}


@pytest.mark.parametrize("ano, esperado", [
    (2020, 2020), (2021, 2021), (2026, 2026),
    (2022, 2024), (2023, 2024),  # sem estimativa: a mais próxima já sobre o Censo 2022, não a de 2021
    (2019, 2020), (2027, 2026),
])
def test_ano_da_estimativa(ano, esperado):
    assert ano_da_estimativa(ano, PUBLICADOS) == esperado


def test_ano_da_estimativa_empate_e_lado_vazio():
    assert ano_da_estimativa(2025, {2024, 2026}) == 2026
    assert ano_da_estimativa(2021, {2024, 2025}) is None


def test_instantaneo_versionado():
    populacao = carregar_populacao()
    assert set(populacao["ano"]) == PUBLICADOS
    de_2026 = populacao[populacao["ano"] == 2026]
    assert len(de_2026) == 5571 and de_2026["populacao"].sum() == 214_211_951
    # Boa Esperança do Norte só tem estimativa depois de instalado
    assert set(populacao.loc[populacao["cod_municipio_ibge"] == 5101837, "ano"]) == {2025, 2026}


def _resposta(series):
    return [{"resultados": [{"series": series}]}]


def test_tabela_estimativas_descarta_municipio_inexistente_no_ano(monkeypatch):
    monkeypatch.setattr("eletromobilidade.populacao.MINIMO_MUNICIPIOS", 1)
    series = [{"localidade": {"id": "5101837"}, "serie": {"2024": "...", "2025": "5877"}},
              {"localidade": {"id": "5107925"}, "serie": {"2024": "120985", "2025": "124665"}}]
    tabela = tabela_estimativas(_resposta(series))
    assert tabela.values.tolist() == [[5107925, 2024, 120985], [5101837, 2025, 5877], [5107925, 2025, 124665]]


def test_tabela_estimativas_rejeita_ano_incompleto():
    series = [{"localidade": {"id": "3550308"}, "serie": {"2026": "11904961"}}]
    with pytest.raises(ValueError, match="poucos municípios"):
        tabela_estimativas(_resposta(series))


MUNICIPIOS = pd.DataFrame({"cod_municipio_ibge": [3550308, 3509502], "uf_sigla": ["SP", "SP"],
                           "municipio_ibge": ["São Paulo", "Campinas"]})


@pytest.mark.parametrize("linhas, erro", [
    ("3550308;2026;10\n3550308;2026;11\n3509502;2026;5\n", "repetido"),
    ("3550308;2026;0\n3509502;2026;5\n", "não positiva"),
    ("3550308;2026;10\n3509502;2026;5\n9999999;2026;5\n", "não estão na lista"),
    ("3550308;2026;10\n3509502;2025;5\n", "sem estimativa em 2026"),
])
def test_instantaneo_conferido(tmp_path, linhas, erro):
    caminho = tmp_path / "populacao.csv"
    caminho.write_text("cod_municipio_ibge;ano;populacao\n" + linhas, encoding="utf-8")
    with pytest.raises(ValueError, match=erro):
        carregar_populacao(caminho, MUNICIPIOS)


def test_distrito_com_o_codigo_da_sede_nao_soma_a_populacao_duas_vezes():
    painel = pd.DataFrame({
        "ano": [2025, 2025], "mes": [1, 1],
        "cod_municipio_ibge": pd.array([3539509, 3539509], dtype="Int64"),
        "municipio_norm": ["IBITIUVA", "PITANGUEIRAS"], "frota_total": [1, 25000],
    })
    resultado = populacao_municipal(painel).set_index("municipio_norm")
    estimativa = carregar_populacao().query("ano == 2025 and cod_municipio_ibge == 3539509")["populacao"].item()
    assert resultado.loc["PITANGUEIRAS", "populacao"] == estimativa
    assert pd.isna(resultado.loc["IBITIUVA", "populacao"])


def test_paineis_com_populacao(xlsx_jan):
    base = pipeline.construir_base_combustivel(pipeline.processar_arquivos([xlsx_jan]))
    estimativa = carregar_populacao().query("ano == 2026").set_index("cod_municipio_ibge")["populacao"]
    sp, campinas, niteroi = estimativa[3550308], estimativa[3509502], estimativa[3303302]

    mun = base["combustivel_municipio"].set_index("municipio_norm")
    assert mun.loc["SAO PAULO", "populacao"] == sp and mun.loc["SAO PAULO", "ano_populacao"] == 2026
    assert mun.loc["SAO PAULO", "eletrificada_por_mil_habitantes"] == pytest.approx(175 / sp * 1000)
    assert pd.isna(mun.loc["SEM INFORMACAO", "populacao"])
    assert pd.isna(mun.loc["SEM INFORMACAO", "eletrificada_por_mil_habitantes"])

    uf = base["combustivel_uf"].set_index("uf_sigla")
    assert uf.loc["SP", "populacao"] == sp + campinas and uf.loc["RJ", "populacao"] == niteroi
    brasil = base["combustivel_brasil"].iloc[0]
    assert brasil["populacao"] == sp + campinas + niteroi
    assert brasil["eletrificada_por_mil_habitantes"] == pytest.approx(185 / (sp + campinas + niteroi) * 1000)


# --- resultados publicados ----------------------------------------------------------------

def test_resultados_todo_municipio_tem_populacao_uma_vez_por_mes():
    df = pd.read_parquet(RESULTADOS / "combustivel_municipio.parquet",
                         columns=["data_referencia", "cod_municipio_ibge", "populacao"])
    contagem = (df.dropna(subset=["cod_municipio_ibge"])
                .groupby(["data_referencia", "cod_municipio_ibge"])["populacao"].count())
    fora = contagem[contagem != 1]
    assert fora.empty, f"município sem população, ou com ela em duas linhas do mês: {fora.head(20).to_dict()}"
    assert df.loc[df["cod_municipio_ibge"].isna(), "populacao"].isna().all()


def test_resultados_brasil_soma_os_municipios():
    municipio = pd.read_parquet(RESULTADOS / "combustivel_municipio.parquet",
                                columns=["ano", "mes", "populacao", "frota_eletrificada"])
    brasil = pd.read_csv(RESULTADOS / "combustivel_brasil.csv", sep=";", decimal=",", encoding="utf-8-sig")
    soma = municipio.groupby(["ano", "mes"])[["populacao", "frota_eletrificada"]].sum()
    brasil = brasil.set_index(["ano", "mes"])
    assert (brasil["populacao"] == soma["populacao"]).all()
    assert brasil["eletrificada_por_mil_habitantes"].values == pytest.approx(
        (soma["frota_eletrificada"] / soma["populacao"] * 1000).values)
