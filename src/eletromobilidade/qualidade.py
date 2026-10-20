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
* **Mês ausente.** Os nomes de arquivo do portal não têm padrão estável, então um
  mês cujo nome não seja reconhecido simplesmente não entra — sem erro. No meio da
  série isso aparece como lacuna; na ponta, não aparecia de forma alguma, porque o
  intervalo era fechado pelo último mês presente. ``meses_ausentes`` compara contra
  o calendário, com o fim ancorado no que a fonte publicou.
* **Classe tardia.** O código de combustível plug-in só entra no RENAVAM em
  abr/2022. Antes disso a contagem é zero, o que não significa frota zero: os
  plug-in estavam em ``frota_hibrido``, que não cai quando a classe nova surge.
  Série dessas classes desde o início do período é leitura errada do cadastro.
* **Frota sem rótulo.** Parte da frota não tem combustível aproveitável no
  cadastro (3,6% em set/2026). É o piso de incerteza das participações.

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


MES_AUSENTE = "mês sem arquivo na entrada"


def meses_esperados(primeiro: tuple[int, int], ultimo: tuple[int, int]) -> list[tuple[int, int]]:
    """Todos os meses do calendário de ``primeiro`` a ``ultimo``, inclusive."""
    if primeiro > ultimo:
        return []
    return [(ano, mes) for ano in range(primeiro[0], ultimo[0] + 1) for mes in range(1, 13)
            if primeiro <= (ano, mes) <= ultimo]


def meses_ausentes(presentes: list[tuple[int, int]] | set[tuple[int, int]],
                   ate: tuple[int, int] | None = None) -> list[tuple[int, int]]:
    """Meses do calendário sem arquivo, do primeiro presente até ``ate``.

    ``ate`` deve vir do que a SENATRAN **publicou** (a listagem de ``coleta``), não
    do que foi baixado. Sem ele o intervalo fecha no último mês presente, e um mês
    que falte na ponta fica invisível: a série termina antes e parece completa.
    Como os nomes de arquivo do portal não têm padrão estável, um mês cujo nome não
    seja reconhecido some exatamente assim — sem erro, sem aviso.
    """
    presentes = set(presentes)
    if not presentes:
        return []
    fim = max(presentes) if ate is None else max(ate, max(presentes))
    return [p for p in meses_esperados(min(presentes), fim) if p not in presentes]


CLASSE_TARDIA = "classe sem registro até {}; antes disso os veículos dela estão em outra classe"


def classes_tardias(painel: pd.DataFrame, colunas: list[str]) -> dict[str, tuple[int, int]]:
    """Classes zeradas no início da série que passam a contar depois: ``{coluna: primeiro mês}``.

    Nem todo zero inicial é ausência de veículo — pode ser ausência de *código*. O
    combustível plug-in só entra no RENAVAM em abr/2022; antes disso os plug-in
    eram contados como híbrido, e ``frota_hibrido`` não cai quando a classe nova
    aparece. Traçar a série dessas classes desde o início do período mostra um zero
    falso seguido de salto artificial, que é leitura errada do cadastro.

    Só sinaliza. Separar "o código não existia" de "o veículo não existia" exige a
    documentação da fonte, não o dado.
    """
    if painel.empty:
        return {}
    ordenado = painel.sort_values(["ano", "mes"])
    tardias = {}
    for coluna in colunas:
        if coluna not in ordenado:
            continue
        positivos = ordenado[ordenado[coluna].fillna(0) > 0]
        if positivos.empty or positivos.index[0] == ordenado.index[0]:
            continue
        primeiro = positivos.iloc[0]
        tardias[coluna] = (int(primeiro["ano"]), int(primeiro["mes"]))
    return tardias


def participacao_sem_informacao(painel: pd.DataFrame, coluna: str = "frota_sem_informacao",
                                total: str = "frota_total") -> pd.Series:
    """Fração da frota sem rótulo de combustível aproveitável, por mês.

    O RENAVAM traz rótulo vazio ou não classificável para parte da frota (3,6% em
    set/2026). Não é erro de leitura: é limite do cadastro, e define o piso de
    incerteza de qualquer participação calculada sobre a frota total.
    """
    if painel.empty or coluna not in painel or total not in painel:
        return pd.Series(dtype="float64")
    ordenado = painel.sort_values(["ano", "mes"])
    return (ordenado[coluna] / ordenado[total]).set_axis(
        pd.MultiIndex.from_arrays([ordenado["ano"], ordenado["mes"]], names=["ano", "mes"]))
