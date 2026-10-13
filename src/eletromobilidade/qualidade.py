"""Verificações de qualidade dos arquivos mensais publicados pela SENATRAN.

Problemas encontrados nos arquivos do portal e tratados aqui:

* **Escala x10.** O arquivo de combustível de novembro/2021 traz todas as
  contagens multiplicadas por 10 (Acrelândia/ALCOOL: 600 em vez de 60), o que
  decuplica a frota nacional. Num arquivo real, com milhares de linhas e muitas
  contagens entre 1 e 9, é impossível que todas sejam múltiplas de 10; quando
  isso ocorre, as contagens são divididas por 10.
* **Mês repetido.** O arquivo de janeiro/2022 é idêntico ao de dezembro/2021.
  Um mês idêntico ao anterior é excluído da série (o dado daquele mês não foi
  publicado), em vez de aparecer como estagnação.

Cada ajuste fica registrado nas tabelas ``qualidade_*``.
"""

from __future__ import annotations

import hashlib

import pandas as pd

MINIMO_LINHAS_ESCALA = 1000


def todas_multiplas_de_10(qtd: pd.Series) -> tuple[bool, int]:
    """``(todas as contagens positivas são múltiplas de 10, número de contagens positivas)``."""
    positivos = qtd[qtd.fillna(0) > 0]
    return bool((positivos % 10 == 0).all()), int(len(positivos))


def escala_suspeita(todas_mult_10: bool, n_positivos: int) -> bool:
    return todas_mult_10 and n_positivos >= MINIMO_LINHAS_ESCALA


AJUSTE_ESCALA = "contagens divididas por 10 (todas eram múltiplas de 10 no arquivo publicado)"


def corrigir_escala(df: pd.DataFrame, coluna: str = "qtd_veiculos") -> tuple[pd.DataFrame, str | None]:
    """Divide as contagens por 10 se o arquivo tiver o defeito de escala x10."""
    if escala_suspeita(*todas_multiplas_de_10(df[coluna])):
        return df.assign(**{coluna: df[coluna] // 10}), AJUSTE_ESCALA
    return df, None


def assinatura(df: pd.DataFrame, chave: list[str], coluna: str = "qtd_veiculos") -> str:
    """Hash do conteúdo (chave + contagem), independente da ordem das linhas."""
    tabela = df[chave + [coluna]].astype("string").fillna("").sort_values(chave + [coluna])
    return hashlib.sha1(tabela.to_csv(index=False).encode()).hexdigest()


def meses_repetidos(assinaturas: dict[tuple[int, int], str]) -> dict[tuple[int, int], tuple[int, int]]:
    """Meses cujo conteúdo é idêntico ao do mês anterior disponível: ``{mês: mês original}``."""
    repetidos = {}
    anterior = None
    for periodo in sorted(assinaturas):
        if anterior is not None and assinaturas[periodo] == assinaturas[anterior]:
            repetidos[periodo] = anterior
        else:
            anterior = periodo
    return repetidos
