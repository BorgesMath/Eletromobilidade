import pandas as pd
import pytest

from eletromobilidade import pipeline
from eletromobilidade.base_modelo import processar_arquivos_modelo
from eletromobilidade.cli import main
from eletromobilidade.conciliacao import conciliar_bases

from conftest import LINHAS_JAN, LINHAS_MARCA_MODELO_JAN, escrever_xlsx


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


def test_paineis_combustivel(pasta_dois_meses):
    longo = pipeline.processar_arquivos(pipeline.localizar_arquivos(pasta_dois_meses, "combustivel"))
    base = pipeline.construir_base_combustivel(longo)

    mun = base["combustivel_municipio"].set_index(["mes", "uf_sigla", "municipio_norm"])
    sp_jan = mun.loc[(1, "SP", "SAO PAULO")]
    assert sp_jan["frota_eletrico"] == 100
    assert sp_jan["frota_hibrido"] == 50
    assert sp_jan["frota_hibrido_plug_in"] == 25
    assert sp_jan["frota_total"] == 1000
    assert sp_jan["frota_eletrificada"] == 175
    assert sp_jan["participacao_eletrificada"] == pytest.approx(0.175)
    assert mun.loc[(2, "SP", "SAO PAULO"), "frota_eletrico"] == 120

    uf = base["combustivel_uf"].set_index(["mes", "uf_sigla"])
    assert uf.loc[(1, "SP"), "frota_eletrificada"] == 185
    assert uf.loc[(1, "SP"), "frota_total"] == 1200
    assert uf.loc[(1, "RJ"), "participacao_eletrificada"] == 0

    br = base["combustivel_brasil"].set_index("mes")
    assert br.loc[1, "frota_total"] == sum(l[3] for l in LINHAS_JAN)  # inclui registros sem UF
    assert br.loc[2, "frota_eletrificada"] == 205

    assert base["combustivel_eletrificados"]["eletrificado"].all()
    assert set(base["combustivel_eletrificados"]["classe"]) == {"eletrico", "hibrido", "hibrido_plug_in"}


def test_periodo_duplicado_falha(tmp_path, xlsx_jan):
    escrever_xlsx(tmp_path / "copy_of_combustivel_Janeiro_2026.xlsx", LINHAS_JAN)
    with pytest.raises(ValueError, match="Dois arquivos para 01/2026"):
        pipeline.processar_arquivos(pipeline.localizar_arquivos(tmp_path, "combustivel"))


def test_base_modelo(zip_marca_modelo_jan):
    base = processar_arquivos_modelo([zip_marca_modelo_jan], tamanho_bloco=4)

    mun = base["modelo_municipio"].set_index(["uf_sigla", "municipio_norm"])
    sp = mun.loc[("SP", "SAO PAULO")]
    assert sp["frota_eletrico"] == 98
    assert sp["frota_hibrido"] == 50
    assert sp["frota_hibrido_plug_in"] == 25
    assert sp["frota_hibrido_leve"] == 12
    assert sp["frota_combustao"] == 815
    assert sp["frota_total"] == 1000
    assert sp["frota_eletrificada"] == 173  # híbrido leve fica de fora
    assert mun.loc[("RJ", "NITEROI"), "frota_nao_motorizado"] == 20

    br = base["modelo_brasil"].iloc[0]
    assert br["frota_total"] == sum(l[4] for l in LINHAS_MARCA_MODELO_JAN)

    det = base["modelo_eletrificados"]
    assert set(det["classe"]) == {"eletrico", "hibrido", "hibrido_plug_in", "hibrido_leve"}
    assert det["qtd_veiculos"].sum() == 90 + 8 + 50 + 25 + 12 + 10
    dolphin = det[det["marca_modelo"] == "I/BYD DOLPHIN GS 180EV"].iloc[0]
    assert (dolphin["ano_fabricacao"], dolphin["uf_sigla"], dolphin["mes"]) == (2024, "SP", 1)

    mod = base["modelos_classificados"].set_index("marca_modelo_norm")
    assert mod.loc["VW/GOL 1.0", "qtd_veiculos"] == 197
    assert mod.loc["VW/8.150E DELIVERY", "classe"] == "combustao"
    assert not mod["revisar"].any()


def test_conciliacao(xlsx_jan, zip_marca_modelo_jan):
    tabelas = pipeline.construir_base_combustivel(pipeline.processar_arquivos([xlsx_jan]))
    tabelas |= processar_arquivos_modelo([zip_marca_modelo_jan])
    conc = conciliar_bases(tabelas)

    br = conc["conciliacao_brasil"].iloc[0]
    assert br["total_combustivel"] == br["total_modelo"] == 1507
    assert (br["eletrico_combustivel"], br["eletrico_modelo"], br["eletrico_diferenca"]) == (110, 108, -2)
    assert br["eletrico_razao"] == pytest.approx(108 / 110)
    assert (br["hibrido_plug_in_combustivel"], br["hibrido_plug_in_modelo"]) == (25, 25)
    assert (br["hibrido_combustivel"], br["hibrido_modelo"]) == (50, 50)
    assert (br["hibridos_combustivel"], br["hibridos_modelo"]) == (75, 75)
    assert (br["eletrificada_combustivel"], br["eletrificada_modelo"]) == (185, 183)
    assert br["hibrido_leve_modelo"] == 12

    uf = conc["conciliacao_uf"].set_index("uf_sigla")
    assert uf.loc["SP", "eletrico_diferenca"] == -2
    assert uf.loc["RJ", "eletrico_razao"] != uf.loc["RJ", "eletrico_razao"]  # 0/0 -> nulo

    mun = conc["conciliacao_municipio"].set_index(["uf_sigla", "municipio_norm"])
    assert mun.loc[("SP", "CAMPINAS"), "eletrico_diferenca"] == 0
    assert len(mun) == 4  # SP, Campinas, Niterói e o registro sem UF


def test_cli_processar_grava_saidas(pasta_dois_meses, zip_marca_modelo_jan, tmp_path):
    saida = tmp_path / "saida"
    main(["processar", "--entrada", str(pasta_dois_meses), "--saida", str(saida)])
    nomes = ["frota_combustivel", "combustivel_eletrificados", "combustiveis_classificados",
             "modelo_eletrificados", "modelos_classificados",
             *(f"{p}_{n}" for p in ("combustivel", "modelo", "conciliacao") for n in ("municipio", "uf", "brasil"))]
    for nome in nomes:
        assert (saida / f"{nome}.parquet").exists(), nome
        assert (saida / f"{nome}.csv").exists(), nome
    assert len(pd.read_parquet(saida / "combustivel_brasil.parquet")) == 2
    assert len(pd.read_parquet(saida / "conciliacao_brasil.parquet")) == 1  # só janeiro nas duas bases
    csv = (saida / "combustivel_uf.csv").read_text(encoding="utf-8-sig").splitlines()
    assert csv[0].startswith("ano;mes;data_referencia;uf_sigla")


def test_cache_da_base_modelo(zip_marca_modelo_jan, tmp_path, monkeypatch):
    from eletromobilidade import base_modelo
    from eletromobilidade.modelos import carregar_regras

    cache = tmp_path / "cache"
    primeira = processar_arquivos_modelo([zip_marca_modelo_jan], cache=cache)
    assert len(list(cache.glob("*.parquet"))) == 3

    def proibido(*args, **kwargs):
        raise AssertionError("arquivo relido apesar do cache")

    monkeypatch.setattr(base_modelo, "agregar_arquivo", proibido)
    segunda = processar_arquivos_modelo([zip_marca_modelo_jan], cache=cache)
    for nome in primeira:
        pd.testing.assert_frame_equal(primeira[nome], segunda[nome], check_dtype=False)

    # regras diferentes invalidam o cache
    regras = carregar_regras()
    regras.loc[0, "padrao"] = "^(R|SR)/"
    with pytest.raises(AssertionError, match="relido"):
        processar_arquivos_modelo([zip_marca_modelo_jan], regras=regras, cache=cache)


def test_salvar_limita_csv(tmp_path):
    tabelas = {"pequena": pd.DataFrame({"a": [1, 2]}), "grande": pd.DataFrame({"a": range(10)})}
    (tmp_path / "grande.csv").write_text("antigo")
    pipeline.salvar(tabelas, tmp_path, limite_csv=5)
    assert (tmp_path / "pequena.csv").exists() and (tmp_path / "pequena.parquet").exists()
    assert (tmp_path / "grande.parquet").exists() and not (tmp_path / "grande.csv").exists()


@pytest.fixture
def poucas_linhas_bastam(monkeypatch):
    from eletromobilidade import qualidade
    monkeypatch.setattr(qualidade, "MINIMO_LINHAS_ESCALA", 3)


def test_qualidade_combustivel_escala_e_mes_repetido(tmp_path, poucas_linhas_bastam):
    escrever_xlsx(tmp_path / "combustivel_Outubro_2021.xlsx", LINHAS_JAN)
    novembro = [(*l[:3], l[3] + 1) for l in LINHAS_JAN]  # mês diferente de outubro
    escrever_xlsx(tmp_path / "combustivel_Novembro_2021.xlsx", [(*l[:3], l[3] * 10) for l in novembro])
    escrever_xlsx(tmp_path / "combustivel_Dezembro_2021.xlsx", LINHAS_JAN[:-1])
    escrever_xlsx(tmp_path / "combustivel_Janeiro_2022.xlsx", LINHAS_JAN[:-1])  # cópia de dezembro

    base = pipeline.construir_base_combustivel(
        pipeline.processar_arquivos(pipeline.localizar_arquivos(tmp_path, "combustivel")))
    br = base["combustivel_brasil"].set_index(["ano", "mes"])["frota_total"]
    total = sum(l[3] for l in LINHAS_JAN)
    assert br.to_dict() == {(2021, 10): total, (2021, 11): total + len(LINHAS_JAN),  # escala corrigida
                            (2021, 12): total - 7}  # jan/2022 excluído

    q = base["qualidade_combustivel"].set_index(["ano", "mes"])
    assert "divididas por 10" in q.loc[(2021, 11), "ajuste"]
    assert q.loc[(2022, 1), "ajuste"].startswith("idêntico a 2021-12")
    assert not q.loc[(2022, 1), "incluido"] and q.loc[(2021, 11), "incluido"]


def test_qualidade_modelo_escala_e_mes_repetido(tmp_path, poucas_linhas_bastam):
    from conftest import escrever_marca_modelo_zip

    julho = [(*l[:4], l[4] + 1) for l in LINHAS_MARCA_MODELO_JAN]  # mês diferente de agosto
    escrever_marca_modelo_zip(tmp_path / "i_frota_marca_e_modelo_ano_julho_2026.zip",
                              [(*l[:4], l[4] * 10) for l in julho])
    escrever_marca_modelo_zip(tmp_path / "i_frota_marca_e_modelo_ano_agosto_2026.zip", LINHAS_MARCA_MODELO_JAN)
    escrever_marca_modelo_zip(tmp_path / "i_frota_marca_e_modelo_ano_setembro_2026.zip", LINHAS_MARCA_MODELO_JAN)

    base = processar_arquivos_modelo(pipeline.localizar_arquivos(tmp_path, "marca_modelo"), cache=tmp_path / "c")
    total = sum(l[4] for l in LINHAS_MARCA_MODELO_JAN)
    assert base["modelo_brasil"].set_index("mes")["frota_total"].to_dict() == {
        7: total + len(LINHAS_MARCA_MODELO_JAN), 8: total}
    assert base["modelo_eletrificados"]["qtd_veiculos"].sum() == 2 * (90 + 8 + 50 + 25 + 12 + 10) + 6
    q = base["qualidade_modelo"].set_index("mes")
    assert "divididas por 10" in q.loc[7, "ajuste"]
    assert q.loc[9, "ajuste"].startswith("idêntico a 2026-08") and not q.loc[9, "incluido"]

    # o ajuste de escala sobrevive ao cache
    q2 = processar_arquivos_modelo(pipeline.localizar_arquivos(tmp_path, "marca_modelo"),
                                   cache=tmp_path / "c")["qualidade_modelo"].set_index("mes")
    assert q2.loc[7, "ajuste"] == q.loc[7, "ajuste"]


def test_cli_desde_ignora_meses_anteriores(tmp_path):
    entrada, saida = tmp_path / "raw", tmp_path / "saida"
    entrada.mkdir()
    escrever_xlsx(entrada / "combustivel_Dezembro_2019.xlsx", LINHAS_JAN)
    escrever_xlsx(entrada / "combustivel_Junho_2020.xlsx", LINHAS_JAN[:-1])
    main(["processar", "--entrada", str(entrada), "--saida", str(saida)])  # padrão: desde 2020-01
    assert pd.read_parquet(saida / "combustivel_brasil.parquet")[["ano", "mes"]].values.tolist() == [[2020, 6]]
    main(["processar", "--entrada", str(entrada), "--saida", str(saida), "--desde", ""])
    assert len(pd.read_parquet(saida / "combustivel_brasil.parquet")) == 2
