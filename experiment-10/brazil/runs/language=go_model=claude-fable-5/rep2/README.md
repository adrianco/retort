# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Go with no external
dependencies, that answers natural-language-driven queries about Brazilian
soccer using six pre-downloaded Kaggle datasets: Brasileirão Série A
(2003-2023), Série B/C, Copa do Brasil, Copa Libertadores matches and the
FIFA player database (18,207 players).

## Specification

[brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md) (mirrored in `TASK.md`)

## What was built

- **`store.go`** - data layer. Loads all six CSVs (UTF-8, BOM-tolerant,
  multiple date formats), normalizes team names ("Palmeiras-SP",
  "Palmeiras", "Sociedade Esportiva Palmeiras", "Botafogo RJ",
  "Atlético Mineiro" vs "Atlético-MG" all resolve consistently, accents
  ignored), and deduplicates matches across overlapping datasets using a
  round-based key plus a date key tolerant of ±1-day kickoff-date
  disagreements. The 2019 Brasileirão, present in three datasets, dedups
  to exactly its real 380 matches.
- **`query.go`** - query engine: match filtering (team, opponent,
  competition, season, date range), head-to-head records, team statistics
  (home/away/all, per-competition breakdown), league standings computed
  from results (3 pts/win; the source-priority rule prevents double
  counting), competition aggregates (avg goals, home win rate, biggest
  wins) and FIFA player search (name, nationality, club, position groups,
  rating/age filters, sorting).
- **`mcp.go`** - minimal MCP server: JSON-RPC 2.0 over newline-delimited
  stdio implementing `initialize`, `ping`, `tools/list`, `tools/call`
  (plus empty `resources/list` / `prompts/list`).
- **`tools.go`** - the eight MCP tools and the formatted text answers.
- **`main.go`** - entry point; `-data` flag selects the CSV directory
  (default `data/kaggle`).

### Exposed MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team/opponent/competition/season/date range, with head-to-head summary |
| `head_to_head` | W/D/L + goals record between two teams, full match list |
| `team_stats` | Team record with venue filter and per-competition breakdown |
| `league_standings` | Season table computed from results (champion, relegation zone) |
| `search_players` | FIFA player search: nationality, club, position group, rating, age |
| `player_info` | Detailed FIFA profile for one player |
| `competition_stats` | Avg goals/match, home win rate, biggest victories |
| `data_summary` | What datasets/competitions/seasons are queryable |

## Build, test, run

```sh
go build -o brazilian-soccer-mcp .   # builds with the Go standard library only
go test ./...                        # BDD-style (Given/When/Then) test suite
./brazilian-soccer-mcp               # serves MCP on stdio
```

Claude Desktop / MCP client configuration:

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

Quick smoke test without a client:

```sh
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"league_standings","arguments":{"season":2019}}}' \
  | ./brazilian-soccer-mcp
```

## Testing

BDD Given/When/Then scenarios in `*_test.go` cover the spec's success
criteria: all six CSVs load and are queryable; team-name variations,
date formats and UTF-8 are handled; cross-dataset dedup is exact for the
2019 season; statistics, head-to-head and standings are correct (2019
champion Flamengo with 90 pts / 28W 6D 4L; 2006 champion São Paulo);
player queries and cross-file queries work; and 25 sample questions are
answered through the real tool handlers, each well under the 5 s budget
(the whole suite, including data loading, runs in about a second).

Notes on data quirks handled: the FIFA dataset has no Flamengo/Palmeiras
club entries (licensing), the extended dataset's kickoff dates can differ
by a day from the canonical sets, and the 2020 COVID season spills into
2021 by calendar date; standings therefore prefer the canonical
season-labelled sources.

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
