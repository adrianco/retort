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

## Implementation

A Model Context Protocol (MCP) server written in Go (no external
dependencies, standard library only). It loads all six CSV files into memory
at startup (~16,600 deduplicated matches across Brasileirão Série A/B/C,
Copa do Brasil and Copa Libertadores, 2003–2023, plus 18,207 FIFA player
profiles) and serves newline-delimited JSON-RPC 2.0 over stdio.

Source files:
- `main.go` — entry point (`-data` flag selects the CSV directory)
- `mcp.go` — MCP/JSON-RPC protocol layer (initialize, ping, tools/list, tools/call)
- `store.go` — CSV loading, cross-dataset deduplication, team-name normalization
  (accents, state suffixes like "Palmeiras-SP", aliases like
  "Athletico Paranaense" = "Atletico-PR", while keeping Atlético-MG/GO/PR distinct)
- `tools.go` — the eight MCP tools

Tools exposed:
- `search_matches` — by team, opponent, competition, season, stage/round, date range
- `get_team_stats` — W/D/L, goals, win rate, per-competition breakdown, home/away venue filter
- `head_to_head` — two-team comparison with recent meetings
- `search_players` — FIFA players by name, nationality, club, position group, min rating
- `get_player_details` — full FIFA profile for one player
- `get_standings` — league table calculated from results (e.g. 2019: Flamengo, 90 pts, Champion)
- `get_competition_stats` — goals per match, home/draw/away split, biggest wins
- `list_competitions` — what is loaded and queryable

### Build, test, run

```sh
go build .          # builds the brazilian-soccer-mcp binary
go test ./...       # BDD (Given/When/Then) scenarios in *_test.go
./brazilian-soccer-mcp -data data/kaggle
```

Claude Desktop / MCP client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/path/to/repo/data/kaggle"]
    }
  }
}
```

### Notes on data quality

- Série A 2012–2019 appears in three datasets; matches are deduplicated by
  competition+season+pairing, merging the extended stats (shots, corners,
  attacks) from BR-Football-Dataset.csv into the canonical row.
- The FIFA snapshot (FIFA 19) does not license every Brazilian club —
  Fluminense, Santos, Grêmio, Cruzeiro etc. are present; Flamengo,
  Palmeiras, Corinthians and São Paulo are not, and Gabriel Barbosa has no
  entry. Player queries for those return a friendly empty result.
