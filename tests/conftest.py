"""Arquivos sintéticos no leiaute dos arquivos mensais da SENATRAN.

Reproduzem o cabeçalho ``UF | Município | Combustível Veículo | Qtd. Veículos``
com UF por extenso em caixa alta. Os números são fictícios.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

CABECALHO = ["UF", "Município", "Combustível Veículo", "Qtd. Veículos"]

LINHAS_JAN = [
    ("SAO PAULO", "SAO PAULO", "ELETRICO/FONTE EXTERNA", 100),
    ("SAO PAULO", "SAO PAULO", "GASOLINA/ELETRICO", 50),
    ("SAO PAULO", "SAO PAULO", "HIBRIDO PLUG-IN", 25),
    ("SAO PAULO", "SAO PAULO", "ALCOOL/GASOLINA", 825),
    ("SAO PAULO", "CAMPINAS", "ELETRICO/FONTE INTERNA", 10),
    ("SAO PAULO", "CAMPINAS", "GASOLINA", 190),
    ("RIO DE JANEIRO", "NITEROI", "DIESEL", 300),
    ("RIO DE JANEIRO", "NITEROI", "Sem Informação", 0),
    ("Sem Informação", "Sem Informação", "GASOLINA", 7),
]


def escrever_xlsx(caminho: Path, linhas, titulo: list[str] | None = None, total: bool = False) -> Path:
    corpo = [CABECALHO] + [list(l) for l in linhas]
    if total:
        corpo.append(["TOTAL", None, None, sum(l[3] for l in linhas)])
    if titulo:
        corpo = [[t, None, None, None] for t in titulo] + [[None] * 4] + corpo
    pd.DataFrame(corpo).to_excel(caminho, header=False, index=False)
    return caminho


@pytest.fixture
def xlsx_jan(tmp_path: Path) -> Path:
    return escrever_xlsx(tmp_path / "D_Frota_por_UF_Municipio_COMBUSTIVEL_Janeiro_2026.xlsx", LINHAS_JAN)
