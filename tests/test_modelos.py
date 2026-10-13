import pandas as pd
import pytest

from eletromobilidade.modelos import ClassificadorModelos, a_revisar, carregar_regras, classificar_modelos

# Textos reais do campo "Marca Modelo" (amostra do arquivo de abril/2026).
CASOS = [
    ("I/BYD DOLPHIN MINI GS5EV", "eletrico"),
    ("I/BYD DOLPHIN GS 180EV", "eletrico"),
    ("I/BYD SONG PRO GS DM", "hibrido_plug_in"),
    ("I/BYD SHARK GS DM", "hibrido_plug_in"),
    ("I/TESLA MODEL Y LONG R", "eletrico"),
    ("I/TAILG VOLTZ EVS", "eletrico"),
    ("I/GWM ORA 03 SKIN BEV48", "eletrico"),
    ("I/GWM HAVAL H6 GT", "hibrido_plug_in"),
    ("I/GWM HAVAL H6 PHEV19", "hibrido_plug_in"),
    ("I/GWM HAVAL H6 HEV2", "hibrido"),
    ("I/VOLVO EX30 E60 ULTRA", "eletrico"),
    ("I/VOLVO XC40 RECHARGE PE", "eletrico"),
    ("I/VOLVO XC40 T5H INSCRIP", "hibrido_plug_in"),
    ("I/VOLVO XC60 T8 POLESTAR", "hibrido_plug_in"),
    ("I/BMW I3 BEV 120AH", "eletrico"),
    ("I/BMW 330E", "hibrido_plug_in"),
    ("I/BMW X5 XDRIVE45E", "hibrido_plug_in"),
    ("I/LEXUS ES300H", "hibrido"),
    ("I/LEXUS NX450H PLUG-IN", "hibrido_plug_in"),
    ("TOYOTA/COROLLA ALTIS HV", "hibrido"),
    ("TOYOTA/CCROSS XRX HYBRID", "hibrido"),
    ("TOYOTA/YCROSS XRE-HYBRID", "hibrido"),
    ("I/TOYOTA PRIUS NGA TOP", "hibrido"),
    ("I/PORSCHE PANAMERA 4EHYB", "hibrido_plug_in"),
    ("I/PORSCHE CAYENNE SCPHEV", "hibrido_plug_in"),
    ("I/AUDI Q5 P-HIBRIDO", "hibrido_plug_in"),
    ("I/JEEP COMPASS S 4XE", "hibrido_plug_in"),
    ("I/RENAULT E-KWID INTENS", "eletrico"),
    ("I/PEUGEOT E EXPERT CARGO", "eletrico"),
    ("FIAT/PULSE AUDACE HYB", "hibrido_leve"),
    ("I/KIA SPORTAGE TMHEV EXP", "hibrido_leve"),
    ("I/CHEV BOLT EUV PREMIER", "eletrico"),
    ("SR/RANDON SR BA 03E", "nao_motorizado"),
    # armadilhas: "E", "EV" e "HEV" que não indicam eletrificação
    ("VW/8.150E DELIVERY", "combustao"),
    ("VW/POLO 1.6 E-FLEX", "combustao"),
    ("HYUNDAI/HB20 10M EVOLUTI", "combustao"),
    ("CHEV/ONIX JOY", "combustao"),
    ("FIAT/UNO ELECTRONIC", "combustao"),
    ("I/PEUGEOT EXPERT CARGO", "combustao"),
    ("I/LR EVOQUE SE", "combustao"),
    ("YAMAHA/YBR 125E", "combustao"),
]


@pytest.mark.parametrize("texto, classe", CASOS)
def test_classificacao_de_modelos_reais(texto, classe):
    assert classificar_modelos(pd.Series([texto]))["classe"].iloc[0] == classe


def test_regra_registrada_e_alinhamento():
    s = pd.Series(["VW/GOL 1.0", None, "I/BYD KING GS DM"], index=[3, 1, 2])
    r = classificar_modelos(s)
    assert list(r.index) == [3, 1, 2]
    assert list(r["classe"]) == ["combustao", "sem_informacao", "hibrido_plug_in"]
    assert r["regra"].iloc[0] == 0 and r["regra"].iloc[2] > 0
    assert list(r["eletrificado"]) == [False, False, True]


def test_hibrido_leve_nao_conta_como_eletrificado():
    assert not classificar_modelos(pd.Series(["FIAT/PULSE AUDACE HYB"]))["eletrificado"].iloc[0]


def test_a_revisar_marca_eletrificada_sem_regra():
    r = classificar_modelos(pd.Series(["I/GAC GS4 ELITE", "VW/GOL 1.0", "I/BYD DOLPHIN GS 180EV"]))
    assert list(a_revisar(r)) == [True, False, False]


def test_classificador_com_cache_igual_ao_direto():
    s1 = pd.Series([t for t, _ in CASOS[:20]])
    s2 = pd.Series([t for t, _ in CASOS[10:]])
    clf = ClassificadorModelos()
    clf(s1)
    assert list(clf(s2)["classe"]) == list(classificar_modelos(s2)["classe"])
    assert len(clf.classificados) == len(CASOS)


def test_regras_invalidas(tmp_path):
    arq = tmp_path / "r.csv"
    arq.write_text("classe;padrao;nota\nfossil;GOL;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fossil"):
        carregar_regras(arq)
    arq.write_text("classe;padrao;nota\neletrico;(BYD;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="regex inválida"):
        carregar_regras(arq)
