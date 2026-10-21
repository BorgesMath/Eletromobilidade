"""Tipo de veículo dos modelos eletrificados: leve, moto, ônibus, caminhão, outros.

"Frota eletrificada" soma automóvel, scooter, ônibus e caminhão num número só, e a
SENATRAN não publica tabela que cruze tipo com combustível: o arquivo por combustível
(``D_``) não tem tipo, e o por tipo (``G_``) não tem combustível. O tipo sai, então,
do modelo, na base por modelo, e só para os modelos do detalhe (eletrificados e
híbridos leves).

Duas fontes. As regras de ``dados/tipos.csv`` (``tipo;padrao;nota``) se aplicam
ao texto normalizado como as de ``dados/modelos.csv``: a primeira que casa vale. E a
tabela PBE Veicular do Inmetro, que só ensaia veículo leve: modelo que casou com
ela (``pbe_categoria`` preenchida) é ``leve``. A precedência:

1. regra que dá tipo não leve (moto, ônibus, caminhão, outros);
2. o PBE, que dá ``leve`` com fonte externa — é a ``origem_tipo`` de quem está nele,
   mesmo que uma regra de leve também case;
3. regra de leve, para o leve que não casou com o PBE (geração antiga, nome
   abreviado como ``TOYOTA/CCROSS``).

Ao contrário da tecnologia, o tipo de um modelo com nome não é ambíguo — um BYD
D9W é ônibus, um Voltz EV1 é scooter —, e as regras foram conferidas modelo a
modelo. O que pode errar é nome novo que uma regra genérica pega mal, e para isso
há duas defesas: regra que dá tipo diferente de ``leve`` a um modelo que está no
PBE vira ``tipo_aviso = 'pbe_diverge'``, e modelo sem regra nem PBE fica sem tipo,
na fila de ``processar``.

Os cinco grupos agregam os tipos do RENAVAM:

* ``leve``: automóvel, camioneta, caminhonete, utilitário (inclui SUV, picape e van);
* ``moto``: motocicleta, motoneta, ciclomotor, triciclo e side-car;
* ``onibus``: ônibus e micro-ônibus;
* ``caminhao``: caminhão, caminhão-trator e chassi-plataforma;
* ``outros``: quadriciclo, trator, reboque e o resto.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pandas as pd

TIPOS = ("leve", "moto", "onibus", "caminhao", "outros")
REGRAS_TIPO_PADRAO = Path(__file__).parent / "dados" / "tipos.csv"


def carregar_regras_tipo(caminho: str | Path | None = None) -> pd.DataFrame:
    """Lê e valida as regras; devolve ``regra`` (a partir de 1), ``tipo``, ``padrao``, ``nota``."""
    caminho = Path(caminho) if caminho is not None else REGRAS_TIPO_PADRAO
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if linha.strip() and linha.count(";") != 2:
            raise ValueError(f"{caminho.name}, linha {numero}: esperados 3 campos separados por ';' "
                             f"(não use ';' dentro da regex nem da nota): {linha[:80]}")
    regras = pd.read_csv(caminho, sep=";", dtype=str, keep_default_na=False, encoding="utf-8")
    invalidos = set(regras["tipo"]) - set(TIPOS)
    if invalidos:
        raise ValueError(f"Tipos desconhecidos em {caminho.name}: {sorted(invalidos)}")
    regras.insert(0, "regra", range(1, len(regras) + 1))
    for numero, padrao in zip(regras["regra"], regras["padrao"]):
        try:
            re.compile(padrao)
        except re.error as erro:
            raise ValueError(f"Regra {numero} de {caminho.name}: regex inválida ({erro})") from None
    return regras


def classificar_tipo(marca_modelo_norm: pd.Series, pbe_categoria: pd.Series,
                     regras: pd.DataFrame | None = None) -> pd.DataFrame:
    """Tipo de cada modelo, alinhado ao índice de entrada.

    Colunas: ``tipo`` (nulo sem regra nem PBE), ``origem_tipo`` (``'regra'``, ``'pbe'``
    ou nulo), ``regra_tipo`` (linha de ``tipos.csv``; 0 sem regra) e ``tipo_aviso``
    (``'pbe_diverge'`` quando a regra dá tipo não leve a modelo que está no PBE).
    """
    regras = carregar_regras_tipo() if regras is None else regras
    texto = marca_modelo_norm.astype("string").fillna("")
    no_pbe = pbe_categoria.fillna("").astype(str).ne("")
    tipo = pd.Series(pd.NA, index=texto.index, dtype="string")
    regra = pd.Series(0, index=texto.index, dtype="int64")
    pendente = pd.Series(True, index=texto.index)
    for numero, tp, padrao in regras[["regra", "tipo", "padrao"]].itertuples(index=False):
        if not pendente.any():
            break
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "This pattern is interpreted as a regular expression")
            casou = pendente & texto.str.contains(padrao, regex=True)
        tipo[casou] = tp
        regra[casou] = numero
        pendente &= ~casou
    origem = pd.Series(pd.NA, index=texto.index, dtype="string")
    origem[regra > 0] = "regra"
    pelo_pbe = no_pbe & (tipo.isna() | tipo.eq("leve"))
    tipo[pelo_pbe] = "leve"
    origem[pelo_pbe] = "pbe"
    aviso = pd.Series(pd.NA, index=texto.index, dtype="string")
    aviso[no_pbe & tipo.ne("leve").fillna(False)] = "pbe_diverge"
    return pd.DataFrame({"tipo": tipo, "origem_tipo": origem, "regra_tipo": regra, "tipo_aviso": aviso})
