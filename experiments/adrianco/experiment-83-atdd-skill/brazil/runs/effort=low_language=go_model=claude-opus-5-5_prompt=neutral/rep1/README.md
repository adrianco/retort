# Brazilian Soccer MCP with spec and basic data sets

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

## MCP Server (Go)

Build and run (stdio JSON-RPC MCP server):

```
go build -o brsoccer .
./brsoccer -data data/kaggle        # MCP over stdin/stdout
./brsoccer -tool standings -args '{"season":2019}'   # one-off CLI query
go test ./...
```

Example Claude Code / desktop config: `{"command": "/path/brsoccer", "args": ["-data", "/path/data/kaggle"]}`

Tools: `search_matches`, `head_to_head`, `team_record`, `team_overview`, `standings`,
`competition_stats`, `biggest_wins`, `rank_teams`, `derbies`, `search_players`,
`players_by_club`, `dataset_info`.

Notes: team names are normalized (accents, state suffixes, "EC"/"FC" tokens, aliases);
matches appearing in several datasets are de-duplicated (same teams within ~1 day);
league standings use a single source file per season to avoid double counting.
The FIFA 19 data has no Flamengo, Palmeiras, São Paulo or Corinthians squads.
