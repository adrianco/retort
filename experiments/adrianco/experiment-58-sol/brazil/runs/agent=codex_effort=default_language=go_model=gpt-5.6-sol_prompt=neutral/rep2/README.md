# Brazilian Soccer MCP Server

A read-only Model Context Protocol server written in Go. It loads every bundled
Kaggle CSV into a normalized in-memory catalog and exposes structured tools for
Brazilian soccer match, team, player, competition, and statistical queries.

## Run

Go 1.26 or newer is required.

```sh
go build -o brazilian-soccer-mcp ./cmd/brazilian-soccer-mcp
./brazilian-soccer-mcp -data data/kaggle
```

The server uses MCP stdio: JSON-RPC is written only to stdout and diagnostics go
to stderr. Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Tools

- `search_matches`: team/opponent, date, competition, season, venue, and stage
- `team_statistics`: W/D/L, points, goals, and home/away records
- `head_to_head`: team comparison with recent meetings
- `search_players`: name, nationality, club, position, and FIFA rating
- `competition_standings`: calculated season tables and champion
- `aggregate_statistics`: scoring rates, result rates, and biggest victories
- `club_overview`: cross-file match record plus FIFA club players
- `dataset_sources`: all six sources and loaded record counts

The `soccer://datasets/summary` resource reports catalog coverage. Match search
returns all source rows; calculations de-duplicate overlapping match exports and
ignore scheduled rows without scores. Player data is the historical FIFA
snapshot bundled in this repository, not a live roster.

## Test

```sh
go test ./...
go test -race ./...
```

The tests cover all six real CSVs, name/date normalization, match and player
lookups, head-to-head records, standings, aggregates, cross-file queries,
performance budgets, and an end-to-end MCP tool call over an in-memory transport.

## Specification

See `TASK.md` and `brazilian-soccer-mcp-guide.md`.

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
