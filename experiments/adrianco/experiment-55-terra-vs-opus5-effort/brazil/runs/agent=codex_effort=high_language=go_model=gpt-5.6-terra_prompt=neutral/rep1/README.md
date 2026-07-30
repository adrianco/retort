# Brazilian Soccer MCP Server

This repository provides a dependency-free Go MCP server over the six supplied
Brazilian soccer CSV datasets. It loads data once at startup, then exposes MCP
tools for match search, team records, head-to-head comparisons, FIFA player
search, calculated standings, and aggregate competition statistics.

Run it over stdio (the normal MCP transport):

```sh
go run .
```

The server reads JSON-RPC messages from standard input and writes only JSON-RPC
responses to standard output. Diagnostics are written to standard error. Pass
`-data /path/to/csv-directory` to override the default `data/kaggle` location.

Available tools include `search_matches`, `team_statistics`, `head_to_head`,
`search_players`, `competition_standings`, `competition_statistics`,
`team_rankings`, and `biggest_wins`. Their schemas and descriptions are
returned by MCP's `tools/list`, so an MCP client or connected LLM can select
and call them naturally.

Team matching is case- and accent-insensitive, removes state suffixes such as
`-SP`, and recognizes common full club-name variants. Dates from the ISO and
Brazilian DD/MM/YYYY sources are normalized during loading.

Run the BDD-named regression suite with:

```sh
go test ./...
```

## Provided data

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
