# Dados locais

Nada aqui vai para o repositório, exceto este arquivo e os `.gitkeep`. Tudo se
regenera a partir da SENATRAN.

| Pasta | O que tem | Quem escreve |
|---|---|---|
| `raw/{tabela}/{ano}/` | Arquivos da SENATRAN como baixados, com o nome original (`combustivel/` ~1 MB por mês, `marca_modelo/` ~130 MB por mês) | `eletromobilidade baixar`, ou cópia manual |
| `raw/ckan_renavam.json` | Última listagem de recursos do CKAN, usada quando a API cai | `baixar` e `links` |
| `interim/marca_modelo/` | Cache dos agregados mensais da base por modelo | `processar` |
| `processed/` | Todas as tabelas, em Parquet e CSV | `processar` |

O que vai para o repositório é a cópia de `processed/` feita por
`eletromobilidade publicar`, em [`resultados/`](../resultados/LEIAME.md). As
tabelas estão descritas em
[`src/eletromobilidade/README.md`](../src/eletromobilidade/README.md#saídas-dataprocessed).
