# Brazilian Soccer MCP

A dependency-free C# MCP stdio server for querying the included Brazilian soccer match datasets and FIFA player database.

## Run

```sh
dotnet run -- --data data/kaggle
```

The server speaks JSON-RPC over standard input/output and implements `initialize`, `tools/list`, `tools/call`, and `ping`. Available tools are `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, and `competition_statistics`.

Team matching is case-, accent-, state-suffix-, and common club-suffix-insensitive. It accepts ISO and Brazilian date formats and loads all six supplied CSV files.

## Test

```sh
dotnet run -- --self-test
```

The self-test validates match/player filtering, team statistics, head-to-head comparisons, standings, normalization, and loading the supplied datasets.

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
