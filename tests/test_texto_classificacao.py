import pandas as pd
import pytest

from eletromobilidade.classificacao import carregar_tabela, classificar, classificar_por_regra
from eletromobilidade.texto import corrigir_mojibake, normalizar_coluna, normalizar_combustivel
from eletromobilidade.ufs import resolver_uf


@pytest.mark.parametrize("bruto, esperado", [
    (" gasolina / elétrico ", "GASOLINA/ELETRICO"),
    ("Híbrido Plugin", "HIBRIDO PLUG-IN"),
    ("HIBRIDO PLUG IN", "HIBRIDO PLUG-IN"),
    ("Sem   Informação", "SEM INFORMACAO"),
    (None, ""),
])
def test_normalizar_combustivel(bruto, esperado):
    assert normalizar_combustivel(bruto) == esperado


def test_normalizar_coluna():
    assert normalizar_coluna("Qtd. Veículos") == "qtd_veiculos"
    assert normalizar_coluna("Combustível Veículo") == "combustivel_veiculo"


def test_resolver_uf():
    assert resolver_uf("SAO PAULO") == ("SP", 35, "Sudeste")
    assert resolver_uf("Espírito Santo") == ("ES", 32, "Sudeste")
    assert resolver_uf("df") == ("DF", 53, "Centro-Oeste")
    assert resolver_uf("Sem Informação") is None


def test_tabela_embutida_e_valida():
    tabela = carregar_tabela()
    assert tabela["ELETRICO/FONTE EXTERNA"] == "eletrico"
    assert tabela["HIBRIDO PLUG-IN"] == "hibrido_plug_in"
    assert tabela["ALCOOL/GASOLINA"] == "combustao"


@pytest.mark.parametrize("rotulo, classe", [
    ("ETANOL/GASOLINA/ELETRICO", "hibrido"),
    ("ELETRICO/BATERIA", "eletrico"),
    ("HIBRIDO PLUG-IN FLEX", "hibrido_plug_in"),
    ("HIDROGENIO/ELETRICO", "celula_combustivel"),
    ("BIODIESEL", "combustao"),
    ("HIBRIDO/ETANOL", "hibrido"),
    ("", "sem_informacao"),
])
def test_regras_para_rotulos_novos(rotulo, classe):
    assert classificar_por_regra(rotulo) == classe


def test_classificar_marca_origem_e_preserva_indice():
    serie = pd.Series(["Elétrico/Fonte Externa", "ETANOL/GASOLINA/ELETRICO", "DIESEL"], index=[10, 20, 30])
    resultado = classificar(serie)
    assert list(resultado.index) == [10, 20, 30]
    assert list(resultado["classe"]) == ["eletrico", "hibrido", "combustao"]
    assert list(resultado["eletrificado"]) == [True, True, False]
    assert list(resultado["origem_classificacao"]) == ["tabela", "regra", "tabela"]


def test_tabela_com_classe_invalida_falha(tmp_path):
    arq = tmp_path / "t.csv"
    arq.write_text("combustivel,classe,nota\nGASOLINA,fossil,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fossil"):
        carregar_tabela(arq)


def test_corrigir_mojibake():
    assert corrigir_mojibake("MunicÃ­pio") == "Município"
    assert corrigir_mojibake("Sem InformaÃ§Ã£o") == "Sem Informação"
    assert corrigir_mojibake("SÃO PAULO") == "SÃO PAULO"
    assert normalizar_coluna("MunicÃ­pio") == "municipio"
