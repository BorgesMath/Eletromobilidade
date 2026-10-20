import pandas as pd

from eletromobilidade.cli import main
from eletromobilidade.publicacao import cobertura

from conftest import escrever_xlsx, LINHAS_JAN


def test_cobertura():
    poucos = pd.DataFrame({"ano": [2019, 2026], "mes": [12, 9]})
    assert cobertura(poucos) == "2 meses (dez/2019, set/2026)"
    serie = pd.DataFrame({"ano": [2019] * 4 + [2020] * 4, "mes": [9, 10, 11, 12, 3, 4, 5, 6]})
    assert cobertura(serie) == "set/2019 a jun/2020, 8 meses; faltam jan/2020, fev/2020"
    longa = pd.DataFrame({"ano": [2019] * 12 + [2026] * 9, "mes": list(range(1, 13)) + list(range(1, 10))})
    assert cobertura(longa) == "jan/2019 a set/2026, 21 meses; faltam 72 meses no intervalo"
    assert cobertura(poucos.iloc[:0]) == "nenhum mês"


def test_publicar(tmp_path, xlsx_jan, zip_marca_modelo_jan):
    escrever_xlsx(tmp_path / "D_Frota_por_UF_Municipio_COMBUSTIVEL_Marco_2026.xlsx", LINHAS_JAN[:-1])
    processados, resultados = tmp_path / "proc", tmp_path / "resultados"
    (resultados).mkdir()
    (resultados / "tabela_antiga.csv").write_text("x")
    main(["processar", "--entrada", str(tmp_path), "--saida", str(processados), "--sem-cache"])
    main(["publicar", "--entrada", str(processados), "--saida", str(resultados)])

    arquivos = {p.name for p in resultados.iterdir()}
    assert {"combustivel_brasil.csv", "conciliacao_uf.csv", "qualidade_modelo.csv",
            "combustivel_municipio.parquet", "modelo_eletrificados.parquet",
            "modelos_dimensao.parquet", "LEIAME.md"} <= arquivos
    assert "frota_combustivel.parquet" not in arquivos and "frota_combustivel.csv" not in arquivos
    assert "combustivel_brasil.parquet" not in arquivos and "combustivel_municipio.csv" not in arquivos
    assert "tabela_antiga.csv" not in arquivos

    leiame = (resultados / "LEIAME.md").read_text(encoding="utf-8")
    assert "**Base por combustível:** 2 meses (jan/2026, mar/2026)" in leiame
    assert "**Base por modelo:** 1 mês (jan/2026)" in leiame
    assert "frota por classe, total" in leiame
    assert "`modelo_eletrificados.parquet`" in leiame


def test_dicionario_descreve_todas_as_colunas(tmp_path, xlsx_jan, zip_marca_modelo_jan):
    processados, resultados = tmp_path / "proc", tmp_path / "resultados"
    main(["processar", "--entrada", str(tmp_path), "--saida", str(processados), "--sem-cache"])
    main(["publicar", "--entrada", str(processados), "--saida", str(resultados)])
    texto = (resultados / "DICIONARIO.md").read_text(encoding="utf-8")
    assert "### `conciliacao_uf.csv`" in texto and "| `eletrico_razao` | decimal |" in texto
    sem_descricao = [l for l in texto.splitlines() if l.startswith("| `") and l.endswith("|  |")]
    assert sem_descricao == []
