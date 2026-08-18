# Brazilian Soccer MCP

A Swift 6 MCP server that indexes the six supplied Brazilian soccer CSV datasets. It exposes MCP tools for match and player searches, team records, head-to-head comparisons, calculated standings, and aggregate statistics. Team matching is accent-insensitive and removes state suffixes (for example, `Flamengo-RJ` matches `Flamengo`).

## Run

```sh
swift run brazilian-soccer-mcp data/kaggle
```

The process uses JSON-RPC 2.0 over standard input/output. Configure your MCP client with `swift run brazilian-soccer-mcp data/kaggle` as its command. Available tools: `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `competition_standings`, and `analyze_statistics`.

## Verify

```sh
swift test
```

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
