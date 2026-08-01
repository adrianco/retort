# Brazilian Soccer MCP with spec and basic data sets

## Run the server

The implementation is a dependency-free MCP server that communicates using JSON-RPC over standard input/output. It loads all six files in `data/kaggle/` at startup.

```sh
dotnet run --project BrazilianSoccerMcp.csproj
```

Available MCP tools are `search_matches`, `team_statistics`, `head_to_head`,
`search_players`, `standings`, `competition_statistics`, and `ask`. Set
`BRAZILIAN_SOCCER_DATA` to use a different directory containing the six CSV files.

Run the included checks with:

```sh
dotnet run --project BrazilianSoccerMcp.Tests.csproj
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
