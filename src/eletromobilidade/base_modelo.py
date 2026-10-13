"""Base de eletromobilidade a partir do arquivo de frota por marca/modelo e ano de fabricação.

O arquivo (~22 milhões de linhas por mês) é lido em blocos. De cada bloco
guardam-se apenas agregados:

* o detalhe dos modelos eletrificados e dos híbridos leves (município x modelo x
  ano de fabricação), que é pequeno;
* a frota por município e classe, para os painéis e as participações;
* a frota por modelo distinto, para auditoria da classificação.

Produtos: ``modelo_eletrificados``, ``modelo_{municipio,uf,brasil}`` e
``modelos_classificados``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .leitura import ler_frota_marca_modelo
from .modelos import CLASSES_ELETRIFICADAS_MODELO, CLASSES_MODELO, ClassificadorModelos, a_revisar
from .pipeline import enriquecer, paineis, periodos_por_arquivo

log = logging.getLogger(__name__)

CLASSES_DETALHE = CLASSES_ELETRIFICADAS_MODELO + ("hibrido_leve",)
_CHAVE_DETALHE = ["uf", "municipio", "marca_modelo", "ano_fabricacao", "classe", "regra"]
_CHAVE_TOTAIS = ["uf", "municipio", "classe"]
_CHAVE_MODELOS = ["marca_modelo_norm", "classe", "regra"]


def _somar(partes: list[pd.DataFrame], chave: list[str]) -> pd.DataFrame:
    if not partes:
        return pd.DataFrame(columns=chave + ["qtd_veiculos"])
    return (pd.concat(partes, ignore_index=True)
            .groupby(chave, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())


def agregar_arquivo(caminho: str | Path, classificador: ClassificadorModelos | None = None,
                    tamanho_bloco: int = 1_000_000) -> dict[str, pd.DataFrame]:
    """Agrega um arquivo mensal; devolve ``detalhe``, ``totais`` e ``modelos`` (sem período)."""
    classificador = classificador or ClassificadorModelos()
    detalhe, totais, modelos = [], [], []
    linhas = 0
    for bloco in ler_frota_marca_modelo(caminho, tamanho_bloco):
        linhas += len(bloco)
        bloco = bloco.join(classificador(bloco["marca_modelo"]))
        sel = bloco[bloco["classe"].isin(CLASSES_DETALHE)]
        detalhe.append(sel.groupby(_CHAVE_DETALHE, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        totais.append(bloco.groupby(_CHAVE_TOTAIS, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        modelos.append(bloco.groupby(_CHAVE_MODELOS, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        log.debug("%s: %d linhas lidas", Path(caminho).name, linhas)
    log.info("%s: %d linhas", Path(caminho).name, linhas)
    return {
        "detalhe": _somar(detalhe, _CHAVE_DETALHE),
        "totais": _somar(totais, _CHAVE_TOTAIS),
        "modelos": _somar(modelos, _CHAVE_MODELOS),
    }


def processar_arquivos_modelo(caminhos: list[Path], regras: pd.DataFrame | None = None,
                              tamanho_bloco: int = 1_000_000) -> dict[str, pd.DataFrame]:
    """Processa arquivos mensais por marca/modelo e monta os produtos da base por modelo."""
    if not caminhos:
        raise FileNotFoundError("Nenhum arquivo de frota por marca/modelo para processar.")
    classificador = ClassificadorModelos(regras)
    detalhe, totais, modelos = [], [], []
    for caminho, periodo in periodos_por_arquivo(caminhos).items():
        log.info("Processando %s", caminho.name)
        agregado = agregar_arquivo(caminho, classificador, tamanho_bloco)
        detalhe.append(enriquecer(agregado["detalhe"], periodo, caminho.name))
        totais.append(enriquecer(agregado["totais"], periodo))
        mod = agregado["modelos"]
        mod.insert(0, "data_referencia", pd.Timestamp(year=periodo[0], month=periodo[1], day=1))
        mod.insert(0, "mes", periodo[1])
        mod.insert(0, "ano", periodo[0])
        modelos.append(mod)

    totais = pd.concat(totais, ignore_index=True)
    modelos = pd.concat(modelos, ignore_index=True)
    modelos["revisar"] = a_revisar(modelos)
    regras_usadas = classificador.regras.set_index("regra")["padrao"]
    modelos["padrao"] = modelos["regra"].map(regras_usadas)
    return {
        "modelo_eletrificados": pd.concat(detalhe, ignore_index=True).sort_values(
            ["ano", "mes", "uf_sigla", "municipio_norm", "classe", "marca_modelo"], na_position="last"
        ).reset_index(drop=True),
        **paineis(totais, "modelo", CLASSES_MODELO, CLASSES_ELETRIFICADAS_MODELO),
        "modelos_classificados": modelos.sort_values(
            ["ano", "mes", "classe", "qtd_veiculos"], ascending=[True, True, True, False]
        ).reset_index(drop=True),
    }
