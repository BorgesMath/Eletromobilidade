"""Interface de linha de comando.

Exemplos::

    eletromobilidade links --ano 2026
    eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 9
    eletromobilidade baixar --tabela combustivel --anos 2025 2026
    eletromobilidade processar --entrada data/raw --saida data/processed
    eletromobilidade publicar
    eletromobilidade pbev tabela-pbev-2026.pdf --ciclo 2026
    eletromobilidade municipios
    eletromobilidade populacao
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from . import coleta, pipeline
from .base_modelo import CLASSES_DETALHE, processar_arquivos_modelo
from .classificacao import carregar_tabela
from .conciliacao import conciliar_bases
from .inmetro import extrair_pbev, gravar_pbev
from .leitura import identificar_tabela, inferir_periodo
from .modelos import carregar_regras, marcas_suspeitas
from .municipios import baixar_municipios_ibge, dimensao_municipio, gravar_municipios, sem_codigo
from .populacao import baixar_estimativas, gravar_populacao
from .publicacao import publicar

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
CACHE = Path("data/interim/marca_modelo")
RESULTADOS = Path("resultados")
INICIO_SERIE = "2020-01"


def _links(args) -> None:
    for link in coleta.listar([args.ano], tuple(args.fontes), cache_ckan=RAW / coleta.ARQUIVO_CACHE_CKAN):
        periodo = f"{link.periodo[0]}-{link.periodo[1]:02d}" if link.periodo else "???????"
        print(f"{periodo}  {link.fonte:<6} {link.tabela:<15} {link.url}")


def _baixar(args) -> None:
    resultado = coleta.baixar_tabela(args.tabela, args.anos, args.destino, args.meses,
                                     tuple(args.fontes), args.sobrescrever)
    for caminho in resultado.baixados:
        print(caminho)
    for link, erro in resultado.falhas:
        print(f"FALHA {link.nome_arquivo}: {erro}")
    if resultado.falhas or not resultado.baixados:
        raise SystemExit(1)


def _processar(args) -> None:
    if args.arquivos:
        caminhos = [Path(a) for a in args.arquivos]
        combustivel = [c for c in caminhos if identificar_tabela(c.name) == "combustivel"]
        marca_modelo = [c for c in caminhos if identificar_tabela(c.name) == "marca_modelo"]
        ignorados = set(caminhos) - set(combustivel) - set(marca_modelo)
        if ignorados:
            logging.warning("Arquivos ignorados (tabela não reconhecida pelo nome): %s",
                            sorted(c.name for c in ignorados))
    else:
        combustivel = pipeline.localizar_arquivos(args.entrada, "combustivel")
        marca_modelo = pipeline.localizar_arquivos(args.entrada, "marca_modelo")
    if args.desde:
        inicio = tuple(int(x) for x in args.desde.split("-"))
        antes = [c for c in combustivel + marca_modelo if (inferir_periodo(c) or (9999, 12)) < inicio]
        if antes:
            logging.info("Ignorando %d arquivo(s) anteriores a %s.", len(antes), args.desde)
        combustivel = [c for c in combustivel if c not in antes]
        marca_modelo = [c for c in marca_modelo if c not in antes]
    if not combustivel and not marca_modelo:
        raise SystemExit("Nenhum arquivo de frota por combustível ou por marca/modelo encontrado.")

    ate = tuple(int(x) for x in args.ate.split("-")) if args.ate else None

    tabelas = {}
    if combustivel:
        longo = pipeline.processar_arquivos(combustivel, carregar_tabela(args.tabela_combustiveis), ate)
        tabelas |= pipeline.construir_base_combustivel(longo)
    if marca_modelo:
        tabelas |= processar_arquivos_modelo(marca_modelo, carregar_regras(args.regras_modelos),
                                             cache=None if args.sem_cache else args.cache)
    if combustivel and marca_modelo:
        tabelas |= conciliar_bases(tabelas)
    municipais = [tabelas[n] for n in ("combustivel_municipio", "modelo_municipio") if n in tabelas]
    tabelas["municipios_dimensao"] = dimensao_municipio(municipais)

    for caminho in pipeline.salvar(tabelas, args.saida, csv=not args.sem_csv):
        print(caminho)

    faltando = sem_codigo(pd.concat(municipais, ignore_index=True))
    if not faltando.empty:
        logging.warning("Municípios sem código IBGE (confira a grafia no IBGE e inclua em "
                        "dados/municipios_grafias.csv):\n%s", faltando.to_string(index=False))
    if "combustiveis_classificados" in tabelas:
        regra = tabelas["combustiveis_classificados"].query("origem_classificacao == 'regra'")
        if not regra.empty:
            logging.warning("Rótulos de combustível classificados por regra (revise e inclua em "
                            "dados/combustiveis.csv):\n%s",
                            regra[["combustivel", "classe", "qtd_veiculos"]].to_string(index=False))
    if "modelos_classificados" in tabelas:
        revisar = tabelas["modelos_classificados"].query("revisar")
        if not revisar.empty:
            logging.warning("Modelos de marcas eletrificadas sem regra (revise dados/modelos.csv):\n%s",
                            revisar[["ano", "mes", "marca_modelo_norm", "qtd_veiculos"]]
                            .head(50).to_string(index=False))
        avisos = tabelas["modelos_classificados"].query("pbe_aviso == 'sem_versao_no_pbe'")
        if not avisos.empty:
            logging.warning("Classe eletrificada que o PBE Veicular não registra para o modelo "
                            "(falso positivo provável; revise dados/modelos.csv):\n%s",
                            avisos[["marca_modelo_norm", "classe", "pbe_classes", "qtd_veiculos"]]
                            .head(30).to_string(index=False))
        classificados = tabelas["modelos_classificados"]
        sem_tipo = classificados[classificados["classe"].isin(CLASSES_DETALHE) & classificados["tipo"].isna()]
        if not sem_tipo.empty:
            logging.warning("Modelos eletrificados sem tipo de veículo (inclua regra em dados/tipos.csv):\n%s",
                            sem_tipo[["ano", "mes", "marca_modelo_norm", "classe", "qtd_veiculos"]]
                            .head(50).to_string(index=False))
        diverge = classificados.query("tipo_aviso == 'pbe_diverge'")
        if not diverge.empty:
            logging.warning("Regra de tipo não leve para modelo que está no PBE Veicular, que só tem leve "
                            "(revise dados/tipos.csv):\n%s",
                            diverge[["marca_modelo_norm", "tipo", "pbe_categoria", "qtd_veiculos"]]
                            .to_string(index=False))
        suspeitas = marcas_suspeitas(tabelas["modelos_classificados"])
        if not suspeitas.empty:
            logging.info("Grafias de marca que parecem variante de outra (avalie incluir em "
                         "dados/marcas.csv):\n%s", suspeitas.head(20).to_string(index=False))


def _pbev(args) -> None:
    print(gravar_pbev(extrair_pbev(args.pdf, args.ciclo), args.saida))


def _municipios(args) -> None:
    print(gravar_municipios(baixar_municipios_ibge(), args.saida))


def _populacao(args) -> None:
    print(gravar_populacao(baixar_estimativas(), args.saida))


def _publicar(args) -> None:
    for caminho in publicar(args.entrada, args.saida):
        print(caminho)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eletromobilidade", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="comando", required=True)

    fontes = dict(nargs="+", choices=coleta.FONTES, default=list(coleta.FONTES),
                  help="fontes consultadas, em ordem de preferência (padrão: ckan portal)")

    p = sub.add_parser("links", help="lista os arquivos publicados para um ano")
    p.add_argument("--ano", type=int, required=True)
    p.add_argument("--fontes", **fontes)
    p.set_defaults(func=_links)

    p = sub.add_parser("baixar", help="baixa os arquivos de uma tabela da SENATRAN")
    p.add_argument("--tabela", choices=coleta.TABELAS, required=True)
    p.add_argument("--anos", type=int, nargs="+", required=True)
    p.add_argument("--meses", type=int, nargs="+", choices=range(1, 13), metavar="MES")
    p.add_argument("--fontes", **fontes)
    p.add_argument("--destino", type=Path, default=RAW)
    p.add_argument("--sobrescrever", action="store_true", help="baixa de novo arquivos já existentes")
    p.set_defaults(func=_baixar)

    p = sub.add_parser("processar", help="gera as bases (combustível, modelo e conciliação) a partir dos arquivos")
    p.add_argument("arquivos", nargs="*", help="arquivos específicos (padrão: todos em --entrada)")
    p.add_argument("--entrada", type=Path, default=RAW)
    p.add_argument("--saida", type=Path, default=PROCESSED)
    p.add_argument("--desde", default=INICIO_SERIE,
                   help=f"primeiro mês da série, AAAA-MM (padrão: {INICIO_SERIE}; '' para usar todos os arquivos)")
    p.add_argument("--ate", help="último mês publicado pela fonte, AAAA-MM (use a saída de 'links'); "
                                 "sem ele, um mês faltando na ponta da série não é detectado")
    p.add_argument("--tabela-combustiveis", type=Path, help="CSV alternativo combustível -> classe")
    p.add_argument("--regras-modelos", type=Path, help="CSV alternativo de regras modelo -> classe")
    p.add_argument("--sem-csv", action="store_true", help="grava apenas Parquet")
    p.add_argument("--cache", type=Path, default=CACHE,
                   help="agregados mensais da base por modelo (padrão: data/interim/marca_modelo)")
    p.add_argument("--sem-cache", action="store_true", help="relê todos os arquivos de marca/modelo")
    p.set_defaults(func=_processar)

    p = sub.add_parser("pbev", help="extrai a tabela PBE Veicular do Inmetro de um PDF para dados/pbev.csv")
    p.add_argument("pdf", type=Path, help="PDF do ciclo, baixado de gov.br/inmetro")
    p.add_argument("--ciclo", type=int, required=True, help="ano do ciclo (ex.: 2026)")
    p.add_argument("--saida", type=Path, help="CSV de destino (padrão: o instantâneo do pacote)")
    p.set_defaults(func=_pbev)

    p = sub.add_parser("municipios", help="baixa a lista de municípios do IBGE para dados/municipios.csv")
    p.add_argument("--saida", type=Path, help="CSV de destino (padrão: o instantâneo do pacote)")
    p.set_defaults(func=_municipios)

    p = sub.add_parser("populacao", help="baixa as estimativas de população do IBGE para dados/populacao.csv")
    p.add_argument("--saida", type=Path, help="CSV de destino (padrão: o instantâneo do pacote)")
    p.set_defaults(func=_populacao)

    p = sub.add_parser("publicar", help="copia painéis, conciliação e auditorias para resultados/ (versionado)")
    p.add_argument("--entrada", type=Path, default=PROCESSED)
    p.add_argument("--saida", type=Path, default=RESULTADOS)
    p.set_defaults(func=_publicar)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
