import pandas as pd
import pytest

from eletromobilidade import pipeline
from eletromobilidade.cli import main

from conftest import LINHAS_JAN, escrever_xlsx


@pytest.fixture
def pasta_dois_meses(tmp_path, xlsx_jan):
    fev = [l if l[2] != "ELETRICO/FONTE EXTERNA" else (*l[:3], 120) for l in LINHAS_JAN]
    escrever_xlsx(tmp_path / "copy_of_D_Frota_por_UF_Municipio_COMBUSTIVEL_Fevereiro_2026.xlsx", fev)
    return tmp_path


def test_processar_arquivo_enriquece(xlsx_jan):
    df = pipeline.processar_arquivo(xlsx_jan)
    assert set(df[["ano", "mes"]].drop_duplicates().itertuples(index=False)) == {(2026, 1)}
    sp = df[df["municipio"] == "SAO PAULO"]
    assert set(sp["uf_sigla"]) == {"SP"} and set(sp["cod_uf_ibge"]) == {35}
    assert df.loc[df["uf"] == "Sem Informação", "uf_sigla"].isna().all()
    assert df["origem_classificacao"].eq("tabela").all()


def test_paineis(pasta_dois_meses):
    longo = pipeline.processar_arquivos(pipeline.localizar_arquivos(pasta_dois_meses))
    base = pipeline.construir_base(longo)

    mun = base["eletromobilidade_municipio"].set_index(["mes", "uf_sigla", "municipio_norm"])
    sp_jan = mun.loc[(1, "SP", "SAO PAULO")]
    assert sp_jan["frota_eletrico"] == 100
    assert sp_jan["frota_hibrido"] == 50
    assert sp_jan["frota_hibrido_plug_in"] == 25
    assert sp_jan["frota_total"] == 1000
    assert sp_jan["frota_eletrificada"] == 175
    assert sp_jan["participacao_eletrificada"] == pytest.approx(0.175)
    assert mun.loc[(2, "SP", "SAO PAULO"), "frota_eletrico"] == 120

    uf = base["eletromobilidade_uf"].set_index(["mes", "uf_sigla"])
    assert uf.loc[(1, "SP"), "frota_eletrificada"] == 185
    assert uf.loc[(1, "SP"), "frota_total"] == 1200
    assert uf.loc[(1, "RJ"), "participacao_eletrificada"] == 0

    br = base["eletromobilidade_brasil"].set_index("mes")
    assert br.loc[1, "frota_total"] == sum(l[3] for l in LINHAS_JAN)  # inclui registros sem UF
    assert br.loc[2, "frota_eletrificada"] == 205

    assert base["eletromobilidade_longo"]["eletrificado"].all()
    assert set(base["eletromobilidade_longo"]["classe"]) == {"eletrico", "hibrido", "hibrido_plug_in"}


def test_periodo_duplicado_falha(tmp_path, xlsx_jan):
    escrever_xlsx(tmp_path / "copy_of_combustivel_Janeiro_2026.xlsx", LINHAS_JAN)
    with pytest.raises(ValueError, match="Dois arquivos para 01/2026"):
        pipeline.processar_arquivos(pipeline.localizar_arquivos(tmp_path))


def test_cli_processar_grava_saidas(pasta_dois_meses, tmp_path):
    saida = tmp_path / "saida"
    main(["processar", "--entrada", str(pasta_dois_meses), "--saida", str(saida)])
    for nome in ("frota_combustivel", "eletromobilidade_municipio", "eletromobilidade_uf",
                 "eletromobilidade_brasil", "eletromobilidade_longo", "combustiveis_classificados"):
        assert (saida / f"{nome}.parquet").exists()
        assert (saida / f"{nome}.csv").exists()
    br = pd.read_parquet(saida / "eletromobilidade_brasil.parquet")
    assert len(br) == 2
    csv = (saida / "eletromobilidade_uf.csv").read_text(encoding="utf-8-sig").splitlines()
    assert csv[0].startswith("ano;mes;data_referencia;uf_sigla")
