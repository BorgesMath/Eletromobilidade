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
    "modelo_tipo_brasil": ("csv", "Base por modelo: eletrificados e híbridos leves por tipo de veículo (leve, moto, ônibus, caminhão, outros), Brasil, por mês. Use participacao_tipo; a contagem absoluta herda a diferença para a base por combustível."),
    "modelo_tipo_uf": ("csv", "Idem, por UF."),
    "modelos_classificados": ("parquet", "Auditoria: cada modelo, classe, regra aplicada, total, marca, marcação 'revisar' e confronto com a tabela PBE Veicular do Inmetro."),
    "modelos_dimensao": ("parquet", "Dimensão de marca e modelo: grafia do RENAVAM, marca canônica e origem, por modelo distinto."),
    "municipios_dimensao": ("parquet", "Dimensão de município: código IBGE, nome oficial, UF e as grafias com que a SENATRAN publicou o município na série."),
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


def _enumerar(itens) -> str:
    itens = [str(i) for i in itens]
    return itens[0] if len(itens) == 1 else f"{', '.join(itens[:-1])} e {itens[-1]}"


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
    if "municipios_dimensao" in tabelas:
        d = tabelas["municipios_dimensao"]
        com_codigo = d["cod_municipio_ibge"].notna()
        varias = int(d["grafias_senatran"].str.contains(" | ", regex=False).sum())
        sem = ", ".join(sorted(d.loc[~com_codigo, "municipio_norm"]))
        linhas.append(f"- **Municípios:** {f'{com_codigo.sum():,}'.replace(',', '.')} com código IBGE, "
                      f"{varias} deles publicados pela SENATRAN com mais de uma grafia na série; "
                      f"sem código: {sem or 'nenhum'}.")
    if "combustivel_brasil" in tabelas and "ano_populacao" in tabelas["combustivel_brasil"]:
        usada = dict(zip(tabelas["combustivel_brasil"]["ano"], tabelas["combustivel_brasil"]["ano_populacao"]))
        texto = f"- **População:** estimativas do IBGE de {_enumerar(sorted(set(usada.values())))}"
        for estimativa in sorted(set(usada.values())):
            sem = sorted(a for a, e in usada.items() if e == estimativa and a != e)
            if sem:
                texto += f"; {_enumerar(sem)}, sem estimativa, {'usam' if len(sem) > 1 else 'usa'} a de {estimativa}"
        linhas.append(texto + ".")
    if "modelo_tipo_brasil" in tabelas:
        br = tabelas["modelo_tipo_brasil"]
        for (ano, mes), mes_br in br.groupby(["ano", "mes"]):
            total = mes_br["frota_eletrificada"].sum()
            sem = mes_br.loc[mes_br["tipo"].isna(), "frota_eletrificada"].sum()
            partes = ", ".join(f"{t} {f / total:.1%}".replace(".", ",") for t, f in
                               mes_br.dropna(subset=["tipo"]).sort_values("frota_eletrificada", ascending=False)
                               [["tipo", "frota_eletrificada"]].values)
            linhas.append(f"- **Tipo de veículo, {_mes(ano, mes)}:** {partes} da frota eletrificada da base por "
                          f"modelo; sem tipo: {sem / total:.2%}".replace(".", ",", 1) + ".")
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
        "Colunas, tipos, fontes e classes: [DICIONARIO.md](DICIONARIO.md). "
        "Limitações e método de conciliação: README do repositório.",
        "",
    ]
    return "\n".join(linhas)


# --- dicionário de dados -----------------------------------------------------------------

FONTES = """\
| Base | Arquivo da SENATRAN | Onde | Colunas originais |
|---|---|---|---|
| Combustível | `D_Frota_por_UF_Municipio_COMBUSTIVEL_<Mês>_<Ano>.xlsx` (mensal) | Páginas anuais [frota-de-veiculos-{ano}](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2026) no gov.br (Ministério dos Transportes/SENATRAN) | UF, Município, Combustível Veículo, Qtd. Veículos |
| Modelo | `I_Frota_por_UF_Municipio_Marca_e_Modelo_Ano_<Mês>_<Ano>.zip` (mensal, ~22 mi de linhas) | Conjunto RENAVAM no [portal de dados abertos](https://dados.transportes.gov.br/dataset/12686da0-3d71-4499-b432-d270f785c907) (API CKAN); alguns meses de 2019–2022 também no gov.br | UF, Município, Marca Modelo, Ano Fabricação Veículo CRV, Qtd. Veículos |

Ambos são extrações do RENAVAM: frota **registrada** no mês de referência (inclui
veículos que já não circulam e não foram baixados). UF vem por extenso; sigla,
código IBGE da UF e região são acrescentados pelo pacote (tabela fixa em
`src/eletromobilidade/ufs.py`). O município vem só pelo nome, e o pacote acrescenta o
código IBGE (`cod_municipio_ibge`) casando UF e nome com a lista oficial da
[API de localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
(instantâneo em `src/eletromobilidade/dados/municipios.csv`) e, onde a grafia da
SENATRAN difere da do IBGE, com `src/eletromobilidade/dados/municipios_grafias.csv`,
conferida à mão. Alguns municípios mudam de grafia no meio da série; o código é a
identidade estável.
População (base por combustível): estimativas anuais do IBGE, tabela
[6579 do SIDRA](https://sidra.ibge.gov.br/tabela/6579) (população residente em 1º de
julho), instantâneo em `src/eletromobilidade/dados/populacao.csv`. Cada mês usa a
estimativa do próprio ano; 2022 e 2023 não têm estimativa e usam a de 2024. Até 2021
as estimativas projetam o Censo 2010 e de 2024 em diante partem do Censo 2022, então a
taxa por habitante de um município muda de base em 2022: ver `ano_populacao`.
Classificação: `src/eletromobilidade/dados/combustiveis.csv` (base por
combustível) e `src/eletromobilidade/dados/modelos.csv` (base por modelo).
Equivalência de grafias de marca: `src/eletromobilidade/dados/marcas.csv`.
Auditoria da classificação contra a tabela PBE Veicular do Inmetro
(propulsão e porte declarados por versão de veículo leve):
`src/eletromobilidade/dados/pbev.csv`, extraída do PDF do ciclo publicado em
[Veículos Automotivos (PBE veicular)](https://www.gov.br/inmetro/pt-br/assuntos/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular).
"""

CLASSES = {
    "eletrico": "Tração 100% elétrica (a bateria). Combustível: ELETRICO/FONTE EXTERNA, ELETRICO/FONTE INTERNA, ELETRICO.",
    "hibrido_plug_in": "Híbrido recarregável na tomada (PHEV), incluindo elétricos com extensor de autonomia (REEV).",
    "hibrido": "Híbrido convencional (HEV): bateria recarregada só pelo motor a combustão e pela frenagem regenerativa.",
    "hibrido_leve": "Só na base por modelo. Híbrido leve (12/48 V): o motor elétrico não traciona sozinho. Fora da frota eletrificada.",
    "celula_combustivel": "Elétrico a célula de combustível (hidrogênio).",
    "combustao": "Somente motor a combustão (inclui flex e GNV).",
    "nao_motorizado": "Só na base por modelo. Reboques (R/) e semirreboques (SR/).",
    "sem_informacao": "Sem informação de combustível ou de modelo.",
}

_COLUNAS = {
    "ano": "Ano do mês de referência do arquivo mensal.",
    "mes": "Mês de referência (1 a 12).",
    "data_referencia": "Primeiro dia do mês de referência (para eixos de tempo).",
    "uf": "UF como publicada pela SENATRAN (por extenso; inclui 'Sem Informação').",
    "uf_sigla": "Sigla da UF; nula quando a UF publicada não é válida ('Sem Informação' etc.).",
    "cod_uf_ibge": "Código IBGE da UF (2 dígitos).",
    "regiao": "Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste).",
    "municipio": "Município como publicado pela SENATRAN.",
    "municipio_norm": "Município como a SENATRAN o grafa, sem acentos, em caixa alta. A grafia muda no meio da "
                      "série em alguns municípios (EMBU virou EMBU DAS ARTES): para identificar o município, "
                      "use cod_municipio_ibge.",
    "cod_municipio_ibge": "Código IBGE do município (7 dígitos). Nulo só nos pseudo-municípios da SENATRAN "
                          "sem UF ('Sem Informação', 'Não Identificado', 'Não se Aplica').",
    "municipio_ibge": "Nome oficial do município no IBGE, com acentos. Nulo nos pseudo-municípios.",
    "grafias_senatran": "Grafias com que a SENATRAN publicou o município na série, na ordem em que "
                        "aparecem, separadas por barra vertical (EMBU, depois EMBU DAS ARTES).",
    "combustivel": "Rótulo do campo combustível do RENAVAM, como publicado.",
    "combustivel_norm": "Rótulo de combustível normalizado (sem acentos, caixa alta, grafias unificadas).",
    "classe": "Classe de tecnologia atribuída (ver a tabela de classes).",
    "eletrificado": "Verdadeiro para eletrico, hibrido_plug_in, hibrido e celula_combustivel.",
    "origem_classificacao": "'tabela' (rótulo listado em combustiveis.csv) ou 'regra' (inferido; revisar).",
    "qtd_veiculos": "Número de veículos registrados.",
    "arquivo_origem": "Arquivo da SENATRAN de onde o dado veio.",
    "marca_modelo": "Texto 'Marca Modelo' do RENAVAM, como publicado (prefixo I/ = importado).",
    "marca_modelo_norm": "Marca Modelo normalizado (sem acentos, caixa alta).",
    "marca_renavam": "Marca como o RENAVAM grafa, sem o prefixo de montadora (I/, IMP/, JTA/) nem de tipo de veículo (R/, SR/, REB/, MR/, MO/, M.A./). Nula quando o texto não traz marca.",
    "marca": "Marca canônica: grafias da mesma empresa unidas por dados/marcas.csv (GM, CHEVROLET e CHEV viram CHEVROLET). Grafia fora da tabela segue como está.",
    "importado": "Verdadeiro quando o texto traz o prefixo I/ ou IMP/ de veículo importado.",
    "origem": "'Importado' ou 'Nacional', conforme o prefixo do texto.",
    "ano_fabricacao": "Ano de fabricação (campo do CRV); nulo quando 'Sem Informação'.",
    "regra": "Número da linha de modelos.csv que definiu a classe (0 = nenhuma regra; classe padrão combustao).",
    "padrao": "Expressão regular da regra aplicada.",
    "revisar": "Verdadeiro para modelo de marca com linha eletrificada que não casou com nenhuma regra.",
    "pbe_classes": "Classes que a linha do modelo tem na tabela PBE Veicular do Inmetro, separadas por barra vertical. Vazio quando o modelo não casou com o PBE (moto, ônibus, caminhão e modelo fora de linha).",
    "pbe_categoria": "Categoria de porte do PBE Veicular (Médio, Picape, Utilitário Esportivo Compacto...). Vazio quando o modelo não casou.",
    "pbe_aviso": "Divergência com o PBE: 'sem_versao_no_pbe' (classe eletrificada que o PBE não registra para o modelo; falso positivo provável) ou 'pbe_so_eletrificado' (classificado combustão, mas toda versão do modelo no PBE é eletrificada; pode ser regra faltando ou geração antiga). Vazio quando não há divergência.",
    "tipo": "Tipo de veículo do modelo: leve (automóvel, SUV, picape, van), moto (inclui motoneta, ciclomotor "
            "e triciclo), onibus, caminhao ou outros. Só para eletrificados e híbridos leves; nulo quando o "
            "modelo não tem regra em dados/tipos.csv nem está no PBE Veicular.",
    "origem_tipo": "'pbe' (o modelo está no PBE Veicular do Inmetro, que só tem veículo leve) ou 'regra' "
                   "(regra de dados/tipos.csv).",
    "regra_tipo": "Número da linha de dados/tipos.csv que casou (0 = nenhuma).",
    "tipo_aviso": "'pbe_diverge' quando a regra dá tipo não leve a um modelo que está no PBE Veicular. Vazio "
                  "quando não há divergência.",
    "participacao_tipo": "Parte do tipo na frota eletrificada do recorte no mês (fração entre 0 e 1).",
    "primeiro_mes": "Primeiro mês em que o rótulo aparece na série.",
    "ultimo_mes": "Último mês em que o rótulo aparece na série.",
    "frota_total": "Frota total do recorte (todas as classes).",
    "frota_eletrificada": "Soma de eletrico, hibrido_plug_in, hibrido e celula_combustivel (sem hibrido_leve).",
    "participacao_eletrificada": "frota_eletrificada / frota_total (fração entre 0 e 1).",
    "hibrido_leve_modelo": "Híbridos leves na base por modelo (sem equivalente na base por combustível).",
    "ano_populacao": "Ano da estimativa de população do IBGE usada no mês: a do próprio ano ou, sem ela, a mais "
                     "próxima do mesmo lado do Censo 2022 (2022 e 2023 usam 2024). Até 2021 a base é o Censo "
                     "2010; de 2024 em diante, o Censo 2022.",
    "populacao": "População residente estimada (IBGE, tabela 6579), em 1º de julho de ano_populacao. Na UF e "
                 "no Brasil, soma dos municípios. Nula nos pseudo-municípios e na linha do distrito de "
                 "Ibitiúva, cuja população já está na de Pitangueiras.",
    "eletrificada_por_mil_habitantes": "frota_eletrificada / populacao x 1000. No Brasil, o numerador inclui a "
                                       "frota sem UF, que não tem população.",
    "arquivo": "Arquivo mensal da SENATRAN; vazio quando o mês do calendário não chegou na entrada.",
    "linhas": "Linhas lidas do arquivo.",
    "ajuste": "Correção ou ressalva do mês: escala x10, mês idêntico ao anterior, mês ausente, "
              "ou classe que só passa a existir no cadastro a partir dali. Vazio se nenhuma.",
    "incluido": "Se o mês entrou na série (falso para mês idêntico ao anterior e para mês ausente).",
    "sem_informacao": "frota_sem_informacao / frota_total no mês (fração entre 0 e 1): parte da frota "
                      "sem rótulo de combustível aproveitável, que é o piso de incerteza das participações.",
}

_INDICADORES = {"total": "frota total", "eletrico": "elétricos", "hibrido_plug_in": "híbridos plug-in",
                "hibrido": "híbridos convencionais", "hibridos": "híbridos plug-in + convencionais",
                "eletrificada": "frota eletrificada"}
_SUFIXOS = {"combustivel": "pela base por combustível", "modelo": "pela base por modelo",
            "diferenca": "diferença modelo − combustível", "razao": "razão modelo / combustível (nula se combustível = 0)"}


# Colunas que numa tabela específica significam outra coisa que no resto.
_COLUNAS_POR_TABELA = {
    ("municipios_dimensao", "municipio_norm"): "Grafia mais recente do município na SENATRAN, sem acentos, "
                                               "em caixa alta. As anteriores estão em grafias_senatran.",
}


def descrever_coluna(nome: str, tabela: str | None = None) -> str:
    if (tabela, nome) in _COLUNAS_POR_TABELA:
        return _COLUNAS_POR_TABELA[(tabela, nome)]
    if nome in _COLUNAS:
        return _COLUNAS[nome]
    if nome.startswith("frota_") and nome[len("frota_"):] in CLASSES:
        return f"Veículos da classe {nome[len('frota_'):]}."
    for ind, rotulo in _INDICADORES.items():
        for suf, texto in _SUFIXOS.items():
            if nome == f"{ind}_{suf}":
                return f"{rotulo.capitalize()}: {texto}."
    return ""


def _tipo(dtype) -> str:
    t = str(dtype).lower()
    if "datetime" in t:
        return "data"
    if "int" in t:
        return "inteiro"
    if "float" in t:
        return "decimal"
    if "bool" in t:
        return "lógico"
    return "texto"


def dicionario(tabelas: dict[str, pd.DataFrame]) -> str:
    linhas = ["# Dicionário de dados", "", "Gerado por `eletromobilidade publicar` a partir das tabelas publicadas.",
              "", "## Fontes", "", FONTES, "## Classes de tecnologia", "", "| Classe | Definição |", "|---|---|"]
    linhas += [f"| `{c}` | {d} |" for c, d in CLASSES.items()]
    linhas += ["", "## Tabelas", ""]
    for nome, df in tabelas.items():
        formato, descricao = PUBLICADAS[nome]
        linhas += [f"### `{nome}.{formato}`", "", descricao, "", "| Coluna | Tipo | Descrição |", "|---|---|---|"]
        linhas += [f"| `{c}` | {_tipo(t)} | {descrever_coluna(c, nome)} |" for c, t in df.dtypes.items()]
        linhas.append("")
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
    caminho = saida / "DICIONARIO.md"
    caminho.write_text(dicionario(tabelas), encoding="utf-8")
    gravados.append(caminho)
    return gravados
