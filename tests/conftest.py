"""Arquivos sintéticos no leiaute dos arquivos mensais da SENATRAN.

Reproduzem o cabeçalho ``UF | Município | Combustível Veículo | Qtd. Veículos``
com UF por extenso em caixa alta. Os números são fictícios.
"""

from __future__ import annotations

import zipfile
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


CABECALHO_MARCA_MODELO = ["UF", "Município", "Marca Modelo", "Ano Fabricação Veículo CRV", "Qtd. Veículos"]

# Mesmos municípios e totais de LINHAS_JAN, com modelos reais do RENAVAM e quantidades fictícias.
LINHAS_MARCA_MODELO_JAN = [
    ("SAO PAULO", "SAO PAULO", "I/BYD DOLPHIN GS 180EV", "2024", 90),        # eletrico
    ("SAO PAULO", "SAO PAULO", "I/TESLA MODEL Y LONG R", "2021", 8),         # eletrico
    ("SAO PAULO", "SAO PAULO", "TOYOTA/CCROSS XRX HYBRID", "2023", 50),      # hibrido
    ("SAO PAULO", "SAO PAULO", "I/BYD SONG PRO GS DM", "2025", 25),          # hibrido_plug_in
    ("SAO PAULO", "SAO PAULO", "FIAT/PULSE AUDACE HYB", "2025", 12),         # hibrido_leve
    ("SAO PAULO", "SAO PAULO", "VW/8.150E DELIVERY", "2008", 15),            # combustao (armadilha)
    ("SAO PAULO", "SAO PAULO", "FIAT/STRADA WORKING", "2020", 800),
    ("SAO PAULO", "CAMPINAS", "I/RENAULT E-KWID INTENS", "2023", 10),        # eletrico
    ("SAO PAULO", "CAMPINAS", "VW/GOL 1.0", "2015", 190),
    ("RIO DE JANEIRO", "NITEROI", "SR/RANDON SR BA 03E", "2022", 20),        # nao_motorizado
    ("RIO DE JANEIRO", "NITEROI", "M.BENZ/OF 1721", "2019", 280),
    ("Sem Informação", "Sem Informação", "VW/GOL 1.0", "Sem Informação", 7),
]


def escrever_marca_modelo_zip(caminho: Path, linhas) -> Path:
    """Zip com texto ``;`` em UTF-8 com BOM e quantidades como ``" 90.0"``, como no portal."""
    texto = ";".join(CABECALHO_MARCA_MODELO) + "\n" + "".join(
        f"{uf};{mun};{mm};{ano}; {qtd:.1f}\n" for uf, mun, mm, ano, qtd in linhas)
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(caminho.with_suffix(".csv").name, texto.encode("utf-8-sig"))
    return caminho


@pytest.fixture
def zip_marca_modelo_jan(tmp_path: Path) -> Path:
    return escrever_marca_modelo_zip(
        tmp_path / "i_frota_por_uf_municipio_marca_e_modelo_ano_janeiro_2026.zip", LINHAS_MARCA_MODELO_JAN)
