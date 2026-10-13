"""Publicação dos resultados em ``resultados/`` (versionado no repositório).

Seleciona, entre as tabelas de ``data/processed``, as que são publicadas:
painéis, conciliação e auditorias em CSV (padrão Excel pt-BR), e as tabelas
por município e de detalhe em Parquet, que é ~5x menor. A base completa por
combustível (``frota_combustivel``) não é publicada: é grande e regenerável.
Um ``LEIAME.md`` descreve cada arquivo e a cobertura real de cada base.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pandas as pd

from .pipeline import salvar

log = logging.getLogger(__name__)

# nome da tabela: (formato, descrição)
PUBLICADAS = {
    "combustivel_brasil": ("csv", "Base por combustível: frota por classe, total, eletrificada e participação, Brasil, por mês."),
    "combustivel_uf": ("csv", "Idem, por UF."),
    "combustivel_municipio": ("parquet", "Idem, por município."),
    "combustivel_eletrificados": ("parquet", "Base por combustível: rótulos eletrificados por município e mês."),
    "combustiveis_classificados": ("csv", "Auditoria: rótulos de combustível, classe atribuída e total de veículos."),
    "modelo_brasil": ("csv", "Base por modelo: frota por classe (inclui plug-in x convencional e híbrido leve), Brasil, por mês."),
    "modelo_uf": ("csv", "Idem, por UF."),
    "modelo_municipio": ("parquet", "Idem, por município."),
    "modelo_eletrificados": ("parquet", "Base por modelo: eletrificados e híbridos leves por município, modelo e ano de fabricação."),
    "modelos_classificados": ("parquet", "Auditoria: cada modelo, classe, regra aplicada, total e marcação 'revisar'."),
    "conciliacao_brasil": ("csv", "Comparação combustível x modelo, Brasil, nos meses presentes nas duas bases."),
    "conciliacao_uf": ("csv", "Idem, por UF."),
    "conciliacao_municipio": ("parquet", "Idem, por município."),
    "qualidade_combustivel": ("csv", "Arquivos mensais da base por combustível: linhas, total, ajustes e inclusão na série."),
    "qualidade_modelo": ("csv", "Idem para a base por modelo."),
}

NOMES_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _mes(ano: int, mes: int) -> str:
    return f"{NOMES_MESES[mes - 1]}/{ano}"


def _n_meses(n: int) -> str:
    return f"{n} {'mês' if n == 1 else 'meses'}"


def cobertura(painel_brasil: pd.DataFrame) -> str:
    """Descrição dos meses presentes num painel nacional.

    Até 6 meses, lista os meses; acima disso, dá o intervalo e as lacunas (listadas
    até 12, contadas acima disso).
    """
    if painel_brasil.empty:
        return "nenhum mês"
    meses = sorted(set(zip(painel_brasil["ano"], painel_brasil["mes"])))
    if len(meses) <= 6:
        return f"{_n_meses(len(meses))} ({', '.join(_mes(*p) for p in meses)})"
    primeiro, ultimo = meses[0], meses[-1]
    todos = [(a, m) for a in range(primeiro[0], ultimo[0] + 1) for m in range(1, 13)
             if primeiro <= (a, m) <= ultimo]
    faltando = [p for p in todos if p not in set(meses)]
    texto = f"{_mes(*primeiro)} a {_mes(*ultimo)}, {_n_meses(len(meses))}"
    if 0 < len(faltando) <= 12:
        texto += f"; faltam {', '.join(_mes(*p) for p in faltando)}"
    elif faltando:
        texto += f"; faltam {_n_meses(len(faltando))} no intervalo"
    return texto


def _commit_atual() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"


def leiame(tabelas: dict[str, pd.DataFrame], gerado_em: pd.Timestamp) -> str:
    linhas = [
        "# Resultados",
        "",
        "Gerado por `eletromobilidade publicar` a partir de `data/processed` "
        f"em {gerado_em:%Y-%m-%d %H:%M} UTC (código no commit `{_commit_atual()}`). "
        "Não edite à mão: rode `processar` e `publicar` de novo.",
        "",
        "## Cobertura",
        "",
    ]
    for base, painel in (("Base por combustível", "combustivel_brasil"), ("Base por modelo", "modelo_brasil"),
                         ("Conciliação", "conciliacao_brasil")):
        if painel in tabelas:
            linhas.append(f"- **{base}:** {cobertura(tabelas[painel])}.")
    for nome in ("qualidade_combustivel", "qualidade_modelo"):
        if nome in tabelas:
            q = tabelas[nome]
            ajustes = q[q["ajuste"].fillna("") != ""]
            for r in ajustes.itertuples():
                linhas.append(f"- Ajuste em {r.arquivo} ({_mes(r.ano, r.mes)}): {r.ajuste}.")
    linhas += ["", "## Arquivos", "", "| Arquivo | Linhas | Conteúdo |", "|---|---:|---|"]
    for nome, (formato, descricao) in PUBLICADAS.items():
        if nome in tabelas:
            n = f"{len(tabelas[nome]):,}".replace(",", ".")
            linhas.append(f"| `{nome}.{formato}` | {n} | {descricao} |")
    linhas += [
        "",
        "CSV: separador `;`, decimal `,`, UTF-8 com BOM (abre direto no Excel pt-BR). "
        "Parquet: ler com `pandas.read_parquet` ou no Power BI/R/DuckDB.",
        "Definições das classes, limitações e método de conciliação: ver o README do repositório.",
        "",
    ]
    return "\n".join(linhas)


def publicar(entrada: str | Path, saida: str | Path, agora: pd.Timestamp | None = None) -> list[Path]:
    """Copia as tabelas publicáveis de ``entrada`` para ``saida`` e escreve o ``LEIAME.md``.

    Arquivos de execuções anteriores que não fazem mais parte da publicação são removidos.
    """
    entrada, saida = Path(entrada), Path(saida)
    tabelas = {nome: pd.read_parquet(entrada / f"{nome}.parquet")
               for nome in PUBLICADAS if (entrada / f"{nome}.parquet").exists()}
    if not tabelas:
        raise FileNotFoundError(f"Nenhuma tabela processada em {entrada}; rode `processar` antes.")
    saida.mkdir(parents=True, exist_ok=True)
    for antigo in saida.glob("*"):
        if antigo.suffix in (".csv", ".parquet"):
            antigo.unlink()

    gravados = []
    for nome, df in tabelas.items():
        formato = PUBLICADAS[nome][0]
        if formato == "csv":
            gravados += [c for c in salvar({nome: df}, saida) if c.suffix == ".csv"]
            (saida / f"{nome}.parquet").unlink(missing_ok=True)
        else:
            gravados += salvar({nome: df}, saida, csv=False)
    agora = agora or pd.Timestamp.now(tz="UTC").tz_localize(None)
    caminho = saida / "LEIAME.md"
    caminho.write_text(leiame(tabelas, agora), encoding="utf-8")
    gravados.append(caminho)
    return gravados
