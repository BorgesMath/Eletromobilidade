# Atualização mensal

A SENATRAN publica os arquivos de um mês ao longo do mês seguinte, sem data
fixa. O ciclo abaixo leva cerca de meia hora, a maior parte dela de download.

## O ciclo

```bash
# 0. ambiente (uma vez)
cd "C:\Users\mathe\OneDrive\Documentos\Eletromobilidade"
.venv\Scripts\activate

# 1. ver o que já está publicado no ano, nas duas fontes
eletromobilidade links --ano 2026

# 2. baixar só o mês novo (para data/raw/{tabela}/{ano}/)
eletromobilidade baixar --tabela combustivel --anos 2026 --meses 10

# 3. reprocessar a série (lê data/raw, grava data/processed)
eletromobilidade -v processar

# 4. republicar resultados/, com LEIAME e DICIONARIO regerados
eletromobilidade publicar

# 5. versionar os resultados
git add resultados/
git commit -m "Resultados: série por combustível até out/2026"
```

Os servidores do gov.br caem no meio de download de 137 MB. O comando `baixar`
já repete com espera exponencial e retoma de onde parou (HTTP `Range`); se
ainda assim falhar, baixe à mão para `data/raw/` mantendo o nome original — o
mês e a tabela são reconhecidos pelo nome do arquivo.

Só o mês novo é lido de novo: os agregados mensais ficam em cache em
`data/interim/`. Mudar as regras de `src/eletromobilidade/dados/modelos.csv`
invalida o cache sozinho.

## Depois de publicar

1. **Rode os testes** (`pytest`). Os de `tests/test_municipios.py` leem
   `resultados/` e falham se o mês novo trouxe um município com grafia que nem o
   IBGE nem `src/eletromobilidade/dados/municipios_grafias.csv` conhecem. O log de
   `processar` já terá listado a grafia, com a frota: confira o nome no IBGE,
   inclua a linha na tabela de grafias, com o código e a razão, e rode `processar`
   e `publicar` de novo. Quando o IBGE criar ou renomear município, atualize a
   lista com `eletromobilidade municipios` antes.
2. **Confira o LEIAME.** `resultados/LEIAME.md` é regerado a cada `publicar` e
   diz a cobertura e os ajustes aplicados. Se um mês novo recebeu ajuste
   automático, é aí que aparece.
3. **Atualize o `.pbix`.** Power BI Desktop > Página Inicial > Atualizar.
   Nenhuma consulta precisa de mudança: todas leem pelo parâmetro
   `PastaResultados`.
4. **Valide.** Confira `[Frota total]` e `[Frota eletrificada]` do Brasil no mês
   novo contra `resultados/combustivel_brasil.csv`. Têm de ser idênticos. A
   tabela de validação de [`MODELO.md`](MODELO.md#validação) tem os valores de
   set/2026 como referência fixa — aqueles não mudam.
5. **Confira a página de cobertura.** Um mês novo tem de aparecer na matriz de
   calor; se não aparecer, o arquivo não entrou na série (coluna `incluido` de
   `fCobertura` em FALSO, normalmente porque era idêntico ao mês anterior).

## Base por modelo

A base por modelo tem um custo muito maior: o arquivo mensal tem cerca de 22
milhões de linhas e 137 MB compactado, e um mês completo leva cerca de 1,5 min
de processamento. Não vale rodar todo mês junto com a de combustível.

```bash
eletromobilidade baixar --tabela marca_modelo --anos 2026 --meses 10
eletromobilidade -v processar
eletromobilidade publicar
```

Hoje a base por modelo tem dois meses (dez/2020 e set/2026). Ampliá-la é item do
[roteiro](../docs/ROTEIRO.md); enquanto for assim, a página 3 do relatório fica
com a tarja de advertência.

## Publicar no Power BI Service

O modelo lê caminhos de arquivo local. Para atualização automática no Service há
dois caminhos, e eles não são equivalentes:

**Gateway pessoal.** Instale o *On-premises data gateway (personal mode)* na
máquina onde a pasta existe e aponte a credencial para o caminho local. Funciona
com o `PastaResultados` como está. Só atualiza enquanto a máquina estiver ligada
— serve para painel de uso interno, não para painel que outras áreas consultam.

**Conector do SharePoint/OneDrive.** A pasta já está em
`OneDrive\Documentos\Eletromobilidade`. Trocando as consultas de
`File.Contents(caminho)` para `SharePoint.Files` ou `Web.Contents` da URL do
OneDrive, o Service atualiza sem gateway. Exige refazer as oito consultas e
guardar a credencial do OneDrive no dataset.

Para um painel que vai circular no MME, o segundo. Enquanto o painel for de
trabalho, o primeiro resolve e custa cinco minutos.

De qualquer forma, **a atualização no Service não dispensa o passo 1 a 5**: o
Service lê `resultados/`, que só muda quando o pipeline Python roda. Não existe
atualização automática de ponta a ponta hoje — a coleta é manual por decisão,
porque a SENATRAN publica sem calendário e os ajustes de qualidade (como o de
nov/2021, com contagens divididas por 10) precisam de olho humano.
