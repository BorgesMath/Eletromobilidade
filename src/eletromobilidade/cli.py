"""Interface de linha de comando.

Exemplos::

    eletromobilidade links --ano 2026
    eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 9
    eletromobilidade baixar --tabela combustivel --anos 2025 2026
    eletromobilidade processar --entrada data/raw --saida data/processed
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import coleta, pipeline
from .base_modelo import processar_arquivos_modelo
from .classificacao import carregar_tabela
from .conciliacao import conciliar_bases
from .leitura import identificar_tabela
from .modelos import carregar_regras

RAW = Path("data/raw")
PROCESSED = Path("data/processed")


def _links(args) -> None:
    for link in coleta.listar([args.ano], tuple(args.fontes)):
        periodo = f"{link.periodo[0]}-{link.periodo[1]:02d}" if link.periodo else "???????"
        print(f"{periodo}  {link.fonte:<6} {link.tabela:<15} {link.url}")


def _baixar(args) -> None:
    caminhos = coleta.baixar_tabela(args.tabela, args.anos, args.destino, args.meses,
                                    tuple(args.fontes), args.sobrescrever)
    for caminho in caminhos:
        print(caminho)
    if not caminhos:
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
    if not combustivel and not marca_modelo:
        raise SystemExit("Nenhum arquivo de frota por combustível ou por marca/modelo encontrado.")

    tabelas = {}
    if combustivel:
        longo = pipeline.processar_arquivos(combustivel, carregar_tabela(args.tabela_combustiveis))
        tabelas |= pipeline.construir_base_combustivel(longo)
    if marca_modelo:
        tabelas |= processar_arquivos_modelo(marca_modelo, carregar_regras(args.regras_modelos))
    if combustivel and marca_modelo:
        tabelas |= conciliar_bases(tabelas)

    for caminho in pipeline.salvar(tabelas, args.saida, csv=not args.sem_csv):
        print(caminho)

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
    p.add_argument("--tabela-combustiveis", type=Path, help="CSV alternativo combustível -> classe")
    p.add_argument("--regras-modelos", type=Path, help="CSV alternativo de regras modelo -> classe")
    p.add_argument("--sem-csv", action="store_true", help="grava apenas Parquet")
    p.set_defaults(func=_processar)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
