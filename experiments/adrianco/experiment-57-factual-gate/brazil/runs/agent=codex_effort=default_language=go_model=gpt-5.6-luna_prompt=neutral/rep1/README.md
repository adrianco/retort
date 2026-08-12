# Brazilian Soccer MCP with spec and basic data sets

## Implementation

This repository now includes a Go MCP server. It loads all six supplied CSV files once at
startup, normalizes team names and dates across the different schemas, and exposes these tools:

- `search_matches` — filter by team, opponent, competition, season, and date range.
- `team_stats` — calculate wins, draws, losses, goals, points, and win rate.
- `search_players` — filter FIFA players by name, nationality, club, position, and rating.
- `standings` — calculate a points table from match results.
- `average_goals` — calculate goals per match.

Run it from the repository root:

```sh
go run ./cmd/brazilian-soccer-mcp
```

Use `-data /path/to/data/kaggle` or `SOCCER_DATA_DIR` when the CSV directory is elsewhere.
The process reads newline-delimited JSON-RPC messages from stdin and writes MCP responses to
stdout. It implements `initialize`, `tools/list`, and `tools/call`.

Run the test suite and build with:

```sh
GOCACHE=/tmp/brazilian-soccer-go-cache go test ./...
GOCACHE=/tmp/brazilian-soccer-go-cache go build ./...
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
