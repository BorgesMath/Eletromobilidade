"""Interface de linha de comando.

Exemplos::

    eletromobilidade links --ano 2025
    eletromobilidade baixar --anos 2025 2026 --meses 1 2 3
    eletromobilidade processar --entrada data/raw --saida data/processed
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import coleta, pipeline
from .classificacao import carregar_tabela

RAW = Path("data/raw")
PROCESSED = Path("data/processed")


def _links(args) -> None:
    for link in coleta.listar_links(args.ano):
        periodo = f"{link.periodo[0]}-{link.periodo[1]:02d}" if link.periodo else "???????"
        print(f"{periodo}  {link.tabela:<15} {link.url}")


def _baixar(args) -> None:
    for caminho in coleta.baixar_frota_combustivel(args.anos, args.destino, args.meses):
        print(caminho)


def _processar(args) -> None:
    caminhos = [Path(a) for a in args.arquivos] if args.arquivos else pipeline.localizar_arquivos(args.entrada)
    tabela = carregar_tabela(args.tabela_combustiveis)
    longo = pipeline.processar_arquivos(caminhos, tabela)
    tabelas = pipeline.construir_base(longo)
    for caminho in pipeline.salvar(tabelas, args.saida, csv=not args.sem_csv):
        print(caminho)

    regra = tabelas["combustiveis_classificados"].query("origem_classificacao == 'regra'")
    if not regra.empty:
        logging.warning("Rótulos classificados por regra (revise e inclua em dados/combustiveis.csv):\n%s",
                        regra[["combustivel", "classe", "qtd_veiculos"]].to_string(index=False))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eletromobilidade", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("links", help="lista os arquivos publicados na página de um ano")
    p.add_argument("--ano", type=int, required=True)
    p.set_defaults(func=_links)

    p = sub.add_parser("baixar", help="baixa os arquivos de frota por município e combustível")
    p.add_argument("--anos", type=int, nargs="+", required=True)
    p.add_argument("--meses", type=int, nargs="+", choices=range(1, 13), metavar="MES")
    p.add_argument("--destino", type=Path, default=RAW)
    p.set_defaults(func=_baixar)

    p = sub.add_parser("processar", help="gera a base de eletromobilidade a partir dos arquivos baixados")
    p.add_argument("arquivos", nargs="*", help="arquivos específicos (padrão: todos em --entrada)")
    p.add_argument("--entrada", type=Path, default=RAW)
    p.add_argument("--saida", type=Path, default=PROCESSED)
    p.add_argument("--tabela-combustiveis", type=Path, help="CSV alternativo combustível -> classe")
    p.add_argument("--sem-csv", action="store_true", help="grava apenas Parquet")
    p.set_defaults(func=_processar)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
