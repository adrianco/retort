# Brazilian Soccer MCP with spec and basic data sets

## Running the MCP server

This is a dependency-free Swift MCP server using newline-delimited JSON-RPC over standard input/output. It automatically loads all six CSV files from `data/kaggle` relative to the working directory.

```sh
swift run --disable-sandbox brazilian-soccer-mcp
```

Set `BRAZILIAN_SOCCER_DATA` to use another directory. Available tools are `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `data_summary`. Team searches are accent-insensitive and normalize common state suffixes and club-name variants.

Run the included tests with:

```sh
swift test --disable-sandbox
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
