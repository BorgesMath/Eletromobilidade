"""Base de eletromobilidade a partir do arquivo de frota por marca/modelo e ano de fabricação.

O arquivo (~22 milhões de linhas por mês) é lido em blocos. De cada bloco
guardam-se apenas agregados:

* o detalhe dos modelos eletrificados e dos híbridos leves (município x modelo x
  ano de fabricação), que é pequeno;
* a frota por município e classe, para os painéis e as participações;
* a frota por modelo distinto, para auditoria da classificação.

Produtos: ``modelo_eletrificados``, ``modelo_{municipio,uf,brasil}`` e
``modelos_classificados``.

Os agregados de cada arquivo podem ser guardados num diretório de cache: um mês
já processado com as mesmas regras não é relido (útil para séries longas, em
que cada mês leva ~1,5 min). Mudar as regras invalida o cache automaticamente.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pandas as pd

from .leitura import ler_frota_marca_modelo
from .modelos import CLASSES_ELETRIFICADAS_MODELO, CLASSES_MODELO, ClassificadorModelos, a_revisar
from .pipeline import enriquecer, paineis, periodos_por_arquivo, registro_qualidade
from .qualidade import AJUSTE_ESCALA, assinatura, escala_suspeita, meses_repetidos, todas_multiplas_de_10

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
    linhas, multiplas_de_10, positivos = 0, True, 0
    for bloco in ler_frota_marca_modelo(caminho, tamanho_bloco):
        linhas += len(bloco)
        todas, n = todas_multiplas_de_10(bloco["qtd_veiculos"])
        multiplas_de_10, positivos = multiplas_de_10 and todas, positivos + n
        bloco = bloco.join(classificador(bloco["marca_modelo"]))
        sel = bloco[bloco["classe"].isin(CLASSES_DETALHE)]
        detalhe.append(sel.groupby(_CHAVE_DETALHE, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        totais.append(bloco.groupby(_CHAVE_TOTAIS, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        modelos.append(bloco.groupby(_CHAVE_MODELOS, dropna=False, observed=True)["qtd_veiculos"].sum().reset_index())
        log.debug("%s: %d linhas lidas", Path(caminho).name, linhas)
    log.info("%s: %d linhas", Path(caminho).name, linhas)
    agregado = {
        "detalhe": _somar(detalhe, _CHAVE_DETALHE),
        "totais": _somar(totais, _CHAVE_TOTAIS),
        "modelos": _somar(modelos, _CHAVE_MODELOS),
    }
    ajuste = None
    if escala_suspeita(multiplas_de_10, positivos):
        ajuste = AJUSTE_ESCALA
        log.warning("%s: %s.", Path(caminho).name, ajuste)
        for tabela in agregado.values():
            tabela["qtd_veiculos"] = tabela["qtd_veiculos"] // 10
    return {**agregado, "ajuste": ajuste, "linhas": linhas}


def assinatura_regras(regras: pd.DataFrame) -> str:
    """Identificador curto do conteúdo das regras (classe e padrão, na ordem)."""
    return hashlib.sha1(regras[["classe", "padrao"]].to_csv(index=False).encode()).hexdigest()[:12]


def agregar_com_cache(caminho: Path, classificador: ClassificadorModelos, cache: Path | None,
                      tamanho_bloco: int = 1_000_000) -> dict[str, pd.DataFrame]:
    """``agregar_arquivo`` com cache em Parquet, indexado por arquivo (nome e tamanho) e regras."""
    if cache is None:
        return agregar_arquivo(caminho, classificador, tamanho_bloco)
    chave = f"{caminho.stem}__{caminho.stat().st_size}__{assinatura_regras(classificador.regras)}"
    arquivos = {nome: Path(cache) / f"{chave}__{nome}.parquet" for nome in ("detalhe", "totais", "modelos")}
    meta = Path(cache) / f"{chave}__meta.json"
    if meta.exists() and all(a.exists() for a in arquivos.values()):
        log.info("%s: usando cache", caminho.name)
        return {**{nome: pd.read_parquet(a) for nome, a in arquivos.items()},
                **json.loads(meta.read_text(encoding="utf-8"))}
    agregado = agregar_arquivo(caminho, classificador, tamanho_bloco)
    Path(cache).mkdir(parents=True, exist_ok=True)
    for nome, arquivo in arquivos.items():
        temporario = arquivo.with_name(arquivo.name + ".parcial")
        agregado[nome].to_parquet(temporario, index=False)
        temporario.replace(arquivo)
    # meta por último: sua presença indica que o cache do arquivo está completo
    meta.write_text(json.dumps({"ajuste": agregado["ajuste"], "linhas": agregado["linhas"]}), encoding="utf-8")
    return agregado


def processar_arquivos_modelo(caminhos: list[Path], regras: pd.DataFrame | None = None,
                              tamanho_bloco: int = 1_000_000,
                              cache: Path | None = None) -> dict[str, pd.DataFrame]:
    """Processa arquivos mensais por marca/modelo e monta os produtos da base por modelo."""
    if not caminhos:
        raise FileNotFoundError("Nenhum arquivo de frota por marca/modelo para processar.")
    classificador = ClassificadorModelos(regras)
    agregados: dict[tuple[int, int], tuple[Path, dict]] = {}
    for caminho, periodo in periodos_por_arquivo(caminhos).items():
        log.info("Processando %s", caminho.name)
        agregados[periodo] = (caminho, agregar_com_cache(caminho, classificador, cache, tamanho_bloco))

    repetidos = meses_repetidos({p: assinatura(a["totais"], _CHAVE_TOTAIS) for p, (_, a) in agregados.items()})
    qualidade = []
    detalhe, totais, modelos = [], [], []
    for periodo, (caminho, agregado) in sorted(agregados.items()):
        ajustes = [agregado.get("ajuste")]
        if periodo in repetidos:
            original = repetidos[periodo]
            ajustes.append(f"idêntico a {original[0]}-{original[1]:02d}; excluído da série")
            log.warning("%s: %s.", caminho.name, ajustes[-1])
        qualidade.append(registro_qualidade(periodo, caminho.name, agregado.get("linhas"),
                                            int(agregado["totais"]["qtd_veiculos"].sum()), ajustes,
                                            periodo not in repetidos))
        if periodo in repetidos:
            continue
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
        "qualidade_modelo": pd.DataFrame(qualidade),
    }
