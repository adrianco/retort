# Brazilian Soccer MCP with spec and basic data sets

## Running the MCP server

This repository is a dependency-free Elixir MCP server. From this directory, start
it over stdio with:

```sh
mix mcp
```

For MCP clients that require an executable command, build and run the same
stdio server with:

```sh
mix escript.build
./brazilian_soccer_mcp
```

It implements the MCP `initialize`, `tools/list`, and `tools/call` methods. The
available tools are `search_matches`, `team_stats`, `head_to_head`,
`search_players`, `standings`, and `aggregate_stats`. Match searches accept
`team`, `competition`, `season`, `from`, and `to`; player searches accept
`name`, `club`, `nationality`, and `position`.

Run the test suite with `mix test`.

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
