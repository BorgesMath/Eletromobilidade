"""População residente estimada por município (IBGE, Estimativas de População).

Fonte: tabela 6579 do SIDRA, lida pela API de agregados do IBGE — população em 1º de
julho de cada ano, por município. Fica num instantâneo versionado em
``dados/populacao.csv`` (comando ``populacao``), como a lista de municípios.

**Não há estimativa para todo ano.** De 2020 em diante o IBGE publicou 2020, 2021,
2024, 2025 e 2026: 2022 é o ano do Censo, e 2023 ficou sem estimativa. Cada mês da
base usa a estimativa do próprio ano; sem ela, a mais próxima **do mesmo lado do
Censo 2022**. Nada é interpolado, e ``ano_populacao`` diz qual estimativa entrou.

**O lado do Censo importa porque a base das estimativas muda.** Até 2021 elas
projetam o Censo 2010; de 2024 em diante partem do Censo 2022. No Brasil a diferença
entre 2021 e 2024 é de -0,3%, mas 1.709 municípios mudam mais de 10% e 525 mais de
20%, contra seis municípios acima de 10% entre 2020 e 2021. É revisão, não
crescimento. Por isso 2022 e 2023 usam a estimativa de 2024, já sobre o Censo que
mediu aqueles anos, e não a de 2021, que estende uma projeção que o Censo
desmentiu. A troca de base cai em 2022: até dez/2021, base Censo 2010; de 2022 em
diante, Censo 2022. Taxa por habitante de um município comparada através dessa
fronteira mede a revisão junto com a frota.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .municipios import carregar_municipios

log = logging.getLogger(__name__)

URL_PERIODOS = "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos"
URL_ESTIMATIVAS = ("https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/{periodos}"
                   "/variaveis/9324?localidades=N6[all]")
POPULACAO_PADRAO = Path(__file__).parent / "dados" / "populacao.csv"
PRIMEIRO_ANO = 2020   # início da série da base
ANO_CENSO = 2022      # a partir deste ano as estimativas partem do Censo 2022

# Abaixo disto, um ano da resposta não é a lista completa de municípios.
MINIMO_MUNICIPIOS = 5500


def tabela_estimativas(resposta: list[dict]) -> pd.DataFrame:
    """Converte a resposta da API de agregados em ``cod_municipio_ibge``, ``ano``, ``populacao``.

    Município que não existia no ano vem como ``"..."`` e fica de fora.
    """
    series = resposta[0]["resultados"][0]["series"]
    linhas = [(int(s["localidade"]["id"]), int(ano), valor)
              for s in series for ano, valor in s["serie"].items()]
    tabela = pd.DataFrame(linhas, columns=["cod_municipio_ibge", "ano", "populacao"])
    tabela = tabela[tabela["populacao"].str.fullmatch(r"\d+")].astype({"populacao": int})
    por_ano = tabela.groupby("ano").size()
    incompletos = por_ano[por_ano < MINIMO_MUNICIPIOS]
    if len(incompletos):
        raise ValueError(f"A API do IBGE devolveu poucos municípios para {incompletos.to_dict()}.")
    return tabela.sort_values(["ano", "cod_municipio_ibge"]).reset_index(drop=True)


def baixar_estimativas(desde: int = PRIMEIRO_ANO, sessao=None) -> pd.DataFrame:
    """Estimativas de população de todos os anos publicados a partir de ``desde``."""
    from .coleta import criar_sessao

    sessao = sessao or criar_sessao()
    resposta = sessao.get(URL_PERIODOS, timeout=60)
    resposta.raise_for_status()
    anos = [p["id"] for p in resposta.json() if int(p["id"]) >= desde]
    resposta = sessao.get(URL_ESTIMATIVAS.format(periodos="|".join(anos)), timeout=300)
    resposta.raise_for_status()
    return tabela_estimativas(resposta.json())


def gravar_populacao(tabela: pd.DataFrame, caminho: str | Path | None = None) -> Path:
    caminho = Path(caminho) if caminho is not None else POPULACAO_PADRAO
    tabela.to_csv(caminho, sep=";", index=False, encoding="utf-8")
    return caminho


def carregar_populacao(caminho: str | Path | None = None,
                       municipios: pd.DataFrame | None = None) -> pd.DataFrame:
    """Lê o instantâneo das estimativas, conferido contra a lista de municípios.

    Falha com ano repetido para o mesmo município, população não positiva, código que
    não está na lista do IBGE, ou município da lista sem estimativa no ano mais recente.
    """
    caminho = Path(caminho) if caminho is not None else POPULACAO_PADRAO
    municipios = carregar_municipios() if municipios is None else municipios
    tabela = pd.read_csv(caminho, sep=";", dtype=int, encoding="utf-8")
    if tabela.duplicated(["cod_municipio_ibge", "ano"]).any():
        raise ValueError(f"Município com o mesmo ano repetido em {caminho.name}.")
    if (tabela["populacao"] <= 0).any():
        raise ValueError(f"População não positiva em {caminho.name}.")
    codigos = set(municipios["cod_municipio_ibge"])
    desconhecidos = set(tabela["cod_municipio_ibge"]) - codigos
    if desconhecidos:
        raise ValueError(f"Códigos que não estão na lista de municípios em {caminho.name}: "
                         f"{sorted(desconhecidos)[:10]}")
    recente = tabela["ano"].max()
    sem_estimativa = codigos - set(tabela.loc[tabela["ano"] == recente, "cod_municipio_ibge"])
    if sem_estimativa:
        raise ValueError(f"Municípios sem estimativa em {recente} em {caminho.name}: {sorted(sem_estimativa)[:10]}; "
                         "atualize dados/municipios.csv e dados/populacao.csv juntos.")
    return tabela


def ano_da_estimativa(ano: int, disponiveis) -> int | None:
    """Estimativa que vale para ``ano``: a do próprio ano ou a mais próxima do mesmo lado do Censo 2022.

    No empate entre um ano antes e um depois, vale a posterior.
    """
    disponiveis = set(disponiveis)
    if ano in disponiveis:
        return ano
    mesmo_lado = [a for a in disponiveis if (a >= ANO_CENSO) == (ano >= ANO_CENSO)]
    if not mesmo_lado:
        return None
    return min(mesmo_lado, key=lambda a: (abs(a - ano), -a))


def populacao_municipal(painel_municipio: pd.DataFrame, populacao: pd.DataFrame | None = None) -> pd.DataFrame:
    """Acrescenta ``ano_populacao`` e ``populacao`` a um painel no grão mês x município.

    A estimativa entra pelo código IBGE; os pseudo-municípios, sem código, ficam sem
    população. Quando duas grafias da SENATRAN caem no mesmo código no mesmo mês — o
    distrito de Ibitiúva ao lado da sede, Pitangueiras —, a população vai só para a de
    maior frota, para não ser somada duas vezes na UF e no Brasil.
    """
    populacao = carregar_populacao() if populacao is None else populacao
    disponiveis = set(populacao["ano"])
    por_ano = {ano: ano_da_estimativa(ano, disponiveis) for ano in painel_municipio["ano"].unique()}
    painel = painel_municipio.assign(
        ano_populacao=pd.array(painel_municipio["ano"].map(por_ano), dtype="Int64"))
    estimativas = populacao.rename(columns={"ano": "ano_populacao"}).astype(
        {"ano_populacao": "Int64", "cod_municipio_ibge": "Int64", "populacao": "Int64"})
    painel = painel.merge(estimativas, on=["ano_populacao", "cod_municipio_ibge"], how="left",
                          validate="many_to_one")
    pela_frota = painel.sort_values("frota_total", ascending=False, kind="stable")
    repetida = pela_frota.duplicated(["ano", "mes", "cod_municipio_ibge"]) & pela_frota["cod_municipio_ibge"].notna()
    painel.loc[repetida[repetida].index, "populacao"] = pd.NA
    return painel
