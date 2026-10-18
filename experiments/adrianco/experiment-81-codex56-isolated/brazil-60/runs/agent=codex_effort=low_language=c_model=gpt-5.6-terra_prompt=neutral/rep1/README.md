# Brazilian Soccer MCP with spec and basic data sets

## Run

Build and run the stdio MCP server with:

```sh
make
./soccer_mcp
```

The server uses newline-delimited JSON-RPC on standard input/output.  After the
normal `initialize` / `notifications/initialized` lifecycle it exposes
`query_matches`, `team_stats`, `head_to_head`, `standings`, `search_players`,
and `aggregate_stats` through `tools/list`.  Run `make test` for an end-to-end
protocol and query smoke suite.

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
