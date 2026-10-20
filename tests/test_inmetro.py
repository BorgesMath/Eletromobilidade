import pandas as pd
import pytest

from eletromobilidade.inmetro import (PROPULSAO_CLASSE, _aviso, _candidatos, _texto_do_modelo,
                                      auditar_com_pbev, carregar_pbev, propulsoes_por_modelo)

# A linha do modelo no PBE, no formato do instantâneo. Casos reais de set/2026.
PBEV = pd.DataFrame(
    columns=["ciclo", "categoria", "marca", "modelo", "versao", "motor", "propulsao", "transmissao", "classe"],
    data=[
        # Corolla existe nas duas propulsões: é o caso que proíbe reduzir o modelo a uma classe.
        [2026, "Médio", "TOYOTA", "Corolla", "GLi", "2.0 - 16V", "Combustão", "CVT", "combustao"],
        [2026, "Médio", "TOYOTA", "Corolla", "Altis Hybrid", "1.8 - 16V", "Híbrido", "CVT", "hibrido"],
        # Grafia do modelo com espaço, que o RENAVAM abrevia sem espaço.
        [2026, "Utilitário Esportivo Compacto", "CAOA CHERY", "Tiggo 8", "Txs", "1.6T", "Plug-in", "DCT-7",
         "hibrido_plug_in"],
        # Linha só eletrificada.
        [2026, "Utilitário Esportivo Grande", "HONDA", "CR-V", "EXL", "2.0 - 16V", "Híbrido", "CVT", "hibrido"],
        [2026, "Sub Compacto", "BYD", "Dolphin Mini", "GS", "Elétrico", "Elétrico", "(MTA)", "eletrico"],
    ],
)


def test_texto_do_modelo_descarta_prefixo_e_marca():
    s = pd.Series(["TOYOTA/COROLLA ALTIS HV", "I/CAOACHERY TIGGO8 PHEV", "SR/RANDON SR CA"])
    assert list(_texto_do_modelo(s)) == ["COROLLA ALTIS HV", "TIGGO8 PHEV", "SR CA"]


def test_candidatos_do_mais_longo_ao_mais_curto():
    assert _candidatos("TIGGO8 PRO HA") == ["TIGGO8PROHA", "TIGGO8PRO", "TIGGO8"]
    assert _candidatos("DOLPHIN MINI GS5EV") == ["DOLPHINMINIGS5EV", "DOLPHINMINI", "DOLPHIN"]


def test_propulsoes_guarda_o_conjunto_de_classes():
    p = propulsoes_por_modelo(PBEV).set_index("chave")
    # Corolla tem as duas, e nenhuma vence a outra.
    assert p.loc["TOYOTA|COROLLA", "pbe_classes"] == "combustao|hibrido"
    assert p.loc["TOYOTA|COROLLA", "pbe_versoes"] == 2
    # A marca entra canônica: CAOA CHERY vira CHERY, e o modelo perde o espaço.
    assert "CHERY|TIGGO8" in p.index
    assert p.loc["HONDA|CRV", "pbe_categoria"] == "Utilitário Esportivo Grande"


@pytest.mark.parametrize("classe, classes_pbe, esperado", [
    # Consistente: a classe está no conjunto do modelo.
    ("hibrido", "combustao|hibrido", ""),
    ("combustao", "combustao|hibrido", ""),
    # Sem casamento no PBE: moto, ônibus, modelo fora de linha. Não é divergência.
    ("eletrico", "", ""),
    # Classe eletrificada que o PBE não registra para o modelo: falso positivo provável.
    ("hibrido_plug_in", "combustao", "sem_versao_no_pbe"),
    ("eletrico", "combustao|hibrido", "sem_versao_no_pbe"),
    # Combustão num modelo cuja linha no PBE é toda eletrificada.
    ("combustao", "hibrido", "pbe_so_eletrificado"),
    ("combustao", "eletrico|hibrido_plug_in", "pbe_so_eletrificado"),
    # Híbrido leve nunca acusa: o PBE não tem a categoria e registra como combustão.
    ("hibrido_leve", "combustao", ""),
    ("hibrido_leve", "combustao|hibrido", ""),
    # Não motorizado e sem informação não têm o que confrontar.
    ("nao_motorizado", "combustao", ""),
])
def test_aviso(classe, classes_pbe, esperado):
    assert _aviso(classe, classes_pbe) == esperado


def test_auditar_com_pbev():
    classificados = pd.DataFrame({
        "marca_modelo_norm": ["TOYOTA/COROLLA ALTIS HV", "TOYOTA/COROLLA GLI", "I/CAOACHERY TIGGO8 PHEV",
                              "I/HONDA CR-V LX", "VAMMO/VMOTO COMFORT 4KW", "I/BYD DOLPHIN MINI GS5EV"],
        "classe": ["hibrido", "combustao", "hibrido_plug_in", "combustao", "eletrico", "eletrico"],
        "qtd_veiculos": [8377, 50000, 11572, 39365, 8176, 30000],
    })
    a = auditar_com_pbev(classificados, propulsoes_por_modelo(PBEV)).set_index("marca_modelo_norm")

    # Corolla Hybrid e Corolla GLi convivem na mesma linha do PBE: nenhum dos dois acusa.
    assert a.loc["TOYOTA/COROLLA ALTIS HV", "pbe_aviso"] == ""
    assert a.loc["TOYOTA/COROLLA GLI", "pbe_aviso"] == ""
    # Casou apesar da grafia (CAOACHERY/TIGGO8 contra CAOA CHERY/Tiggo 8) e traz o porte.
    assert a.loc["I/CAOACHERY TIGGO8 PHEV", "pbe_classes"] == "hibrido_plug_in"
    assert a.loc["I/CAOACHERY TIGGO8 PHEV", "pbe_categoria"] == "Utilitário Esportivo Compacto"
    # CR-V a combustão contra linha só híbrida no PBE: aviso para conferir o ano.
    assert a.loc["I/HONDA CR-V LX", "pbe_aviso"] == "pbe_so_eletrificado"
    # Scooter não está no PBE, que é só de veículo leve: sem casamento e sem aviso.
    assert a.loc["VAMMO/VMOTO COMFORT 4KW", "pbe_classes"] == ""
    assert a.loc["VAMMO/VMOTO COMFORT 4KW", "pbe_aviso"] == ""


def test_auditar_preserva_linhas_e_colunas():
    classificados = pd.DataFrame({"marca_modelo_norm": ["TOYOTA/COROLLA GLI"], "classe": ["combustao"],
                                  "qtd_veiculos": [1], "regra": [0]})
    a = auditar_com_pbev(classificados, propulsoes_por_modelo(PBEV))
    assert len(a) == 1
    assert {"regra", "qtd_veiculos", "pbe_classes", "pbe_categoria", "pbe_aviso"} <= set(a.columns)


def test_instantaneo_versionado_carrega():
    pbev = carregar_pbev()
    assert len(pbev) > 300
    assert set(pbev["classe"]) <= set(PROPULSAO_CLASSE.values())
    # O ciclo 2026 tem as quatro propulsões e nenhuma marca ou modelo vazio.
    ciclo = pbev[pbev["ciclo"] == 2026]
    assert set(ciclo["classe"]) == set(PROPULSAO_CLASSE.values())
    assert not (ciclo["marca"] == "").any() and not (ciclo["modelo"] == "").any()


def test_classe_desconhecida_no_instantaneo(tmp_path):
    arq = tmp_path / "pbev.csv"
    arq.write_text("ciclo;categoria;marca;modelo;versao;motor;propulsao;transmissao;classe\n"
                   "2026;Médio;TOYOTA;Corolla;GLi;2.0;Combustão;CVT;fossil\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fossil"):
        carregar_pbev(arq)
