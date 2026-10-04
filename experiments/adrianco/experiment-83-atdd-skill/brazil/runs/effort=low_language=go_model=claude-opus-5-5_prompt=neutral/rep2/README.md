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

## Go MCP server

Build and run (stdio transport, JSON-RPC 2.0, MCP protocol 2024-11-05):

```
go build -o brsoccer .
./brsoccer -data data/kaggle            # MCP server on stdin/stdout
./brsoccer -call head_to_head '{"team1":"Flamengo","team2":"Fluminense"}'   # one-off query
go test ./...
```

Example Claude Code / Desktop config: `{"command": "/path/to/brsoccer", "args": ["-data", "/path/to/data/kaggle"]}`

Tools: `search_matches`, `head_to_head`, `team_record`, `standings`, `team_rankings`,
`compare_seasons`, `team_competitions`, `derbies`, `search_players`, `player_details`,
`players_by_club`, `team_profile`, `dataset_overview`.

Notes:
- Team names are normalized (accents, state suffixes, full club names, Atlético-MG/PR/GO disambiguation).
- Overlapping sources (Serie A appears in three files) are de-duplicated; standings use a single source per season.
- Matches with `NA` scores (unplayed) are skipped.
- The FIFA 19 dataset omits several Brazilian clubs (Flamengo, Palmeiras, São Paulo, Corinthians).
