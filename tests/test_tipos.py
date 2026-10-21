from pathlib import Path

import pandas as pd
import pytest

from eletromobilidade.base_modelo import CLASSES_DETALHE, processar_arquivos_modelo
from eletromobilidade.tipos import carregar_regras_tipo, classificar_tipo

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"


def _tipo(texto: str, pbe: str = "") -> pd.Series:
    return classificar_tipo(pd.Series([texto]), pd.Series([pbe])).iloc[0]


@pytest.mark.parametrize("texto, esperado", [
    ("TOYOTA/CCROSS XRX HYBRID", "leve"),       # fora do PBE pela abreviação
    ("I/BYD D1 GS 180EV", "leve"),              # D1 é carro; o ônibus da BYD é D9/D11
    ("BYD/D9W 20.410", "onibus"),
    ("BYD/INDUSCAR MILLEN U", "onibus"),        # carroceria Caio sobre chassi BYD
    ("M.BENZ/EO500 U2134", "onibus"),
    ("I/BYD ET8A", "caminhao"),
    ("VW/E-DELIVERY 11.4", "caminhao"),
    ("I/JAC IEV1200T PLUS", "caminhao"),
    ("I/JAC EJT9.5", "caminhao"),
    ("I/JAC EJV12", "leve"),                    # furgão: o sufixo V é van, T é caminhão
    ("I/VOLVO FM ELECTRIC 6X2T", "caminhao"),
    ("I/VOLVO XC40 6 PLUS", "leve"),
    ("VAMMO/VMOTO COMFORT 4KW", "moto"),
    ("MOTOCHEFE/X11 3.000W", "moto"),
    ("I/JIANGSU DM 500 W GY", "moto"),
    ("YAMAHA/RAY ZR HYBRID", "moto"),
    ("SHINERAY/PT3", "moto"),
    ("I/BMW CE 04", "moto"),
    ("I/BMW I4 M50", "leve"),
    ("I/SAIC MGS5 EV 49KWH LUX", "leve"),       # KWH é bateria, não potência de scooter
    ("I/TOYOTA RAV4H 25L S 4WD", "leve"),       # 4WD não é potência em W
    ("I/SR XUZHOU HB L9102DT", "outros"),
])
def test_tipo_de_modelos_reais(texto, esperado):
    resultado = _tipo(texto)
    assert resultado["tipo"] == esperado and resultado["origem_tipo"] == "regra"


def test_sem_regra_nem_pbe_fica_sem_tipo():
    resultado = _tipo("I/GUANGZHOU Z1 ELETRIC")
    assert pd.isna(resultado["tipo"]) and pd.isna(resultado["origem_tipo"]) and resultado["regra_tipo"] == 0


def test_pbe_e_a_origem_do_leve():
    # a BYD eT3 é van: o PBE a registra como comercial, e nenhuma regra de caminhão a pega
    van = _tipo("I/BYD ET3", "Comercial")
    assert (van["tipo"], van["origem_tipo"]) == ("leve", "pbe") and pd.isna(van["tipo_aviso"])
    # leve por regra e no PBE: a origem registrada é o PBE, que é fonte externa
    corolla = _tipo("TOYOTA/COROLLA ALTIS HV", "Médio")
    assert (corolla["tipo"], corolla["origem_tipo"]) == ("leve", "pbe")
    # modelo que não tem regra mas está no PBE
    assert _tipo("I/MARCA NOVA QUALQUER", "Compacto")["tipo"] == "leve"


def test_regra_nao_leve_para_modelo_do_pbe_e_aviso():
    resultado = _tipo("I/BYD ET8A", "Comercial")
    assert (resultado["tipo"], resultado["tipo_aviso"]) == ("caminhao", "pbe_diverge")


@pytest.mark.parametrize("linha, erro", [
    ("bicicleta;\\bX\\b;tipo que não existe\n", "Tipos desconhecidos"),
    ("moto;(;regex quebrada\n", "regex inválida"),
    ("moto;\\bX\\b;nota; com ponto e vírgula\n", "3 campos"),
])
def test_regras_invalidas(tmp_path, linha, erro):
    caminho = tmp_path / "tipos.csv"
    caminho.write_text("tipo;padrao;nota\n" + linha, encoding="utf-8")
    with pytest.raises(ValueError, match=erro):
        carregar_regras_tipo(caminho)


def test_base_por_modelo_traz_tipo_e_paineis_por_tipo(zip_marca_modelo_jan):
    tabelas = processar_arquivos_modelo([zip_marca_modelo_jan])
    assert tabelas["modelo_eletrificados"]["tipo"].eq("leve").all()
    assert tabelas["modelos_dimensao"]["tipo"].eq("leve").all()
    classificados = tabelas["modelos_classificados"]
    assert classificados.loc[~classificados["classe"].isin(CLASSES_DETALHE), "tipo"].isna().all()
    brasil = tabelas["modelo_tipo_brasil"]
    assert brasil[["tipo", "participacao_tipo"]].values.tolist() == [["leve", 1.0]]
    # Dolphin 90 + Tesla 8 + Corolla Cross 50 + Song DM 25 + E-Kwid 10; o híbrido leve fica de fora
    assert brasil["frota_eletrificada"].item() == 183 and brasil["frota_hibrido_leve"].item() == 12


# --- resultados publicados ----------------------------------------------------------------

def test_resultados_nenhuma_regra_de_tipo_contradiz_o_pbe():
    classificados = pd.read_parquet(RESULTADOS / "modelos_classificados.parquet")
    diverge = classificados.query("tipo_aviso == 'pbe_diverge'")
    assert diverge.empty, diverge[["marca_modelo_norm", "tipo", "pbe_categoria"]].values.tolist()


def test_resultados_frota_sem_tipo_e_residual():
    """Até 0,1% da frota do detalhe em cada mês pode ficar sem tipo — os nomes que
    nenhuma fonte identifica. Acima disso, falta regra em dados/tipos.csv."""
    eletrificados = pd.read_parquet(RESULTADOS / "modelo_eletrificados.parquet", columns=["ano", "mes", "tipo",
                                                                                        "qtd_veiculos"])
    por_mes = eletrificados.groupby(["ano", "mes"]).apply(
        lambda m: m.loc[m["tipo"].isna(), "qtd_veiculos"].sum() / m["qtd_veiculos"].sum(), include_groups=False)
    assert (por_mes <= 0.001).all(), por_mes.to_dict()


def test_resultados_paineis_por_tipo_fecham_com_o_detalhe():
    eletrificados = pd.read_parquet(RESULTADOS / "modelo_eletrificados.parquet")
    brasil = pd.read_csv(RESULTADOS / "modelo_tipo_brasil.csv", sep=";", decimal=",", encoding="utf-8-sig")
    soma = eletrificados.groupby(["ano", "mes"])["qtd_veiculos"].sum()
    colunas = [c for c in brasil.columns if c.startswith("frota_") and c != "frota_eletrificada"]
    assert (brasil.groupby(["ano", "mes"])[colunas].sum().sum(axis=1) == soma).all()
    assert brasil.groupby(["ano", "mes"])["participacao_tipo"].sum().values == pytest.approx(1.0)
