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

## Implementation (Go)

A dependency-free Go MCP server (`go 1.22+`, standard library only) that loads the six CSV
files into an in-memory knowledge graph (teams, matches, players) and exposes it as MCP
tools over stdio (newline-delimited JSON-RPC 2.0).

### Build, test, run

```bash
go build -o brsoccer .
go test ./...                       # BDD-style tests against the real CSV files
./brsoccer                          # serve MCP on stdin/stdout (data from ./data/kaggle)
./brsoccer -data /path/to/kaggle    # or set BRSOCCER_DATA_DIR
./brsoccer -call standings -args '{"season": 2019}'   # one-off query without an MCP client
```

MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brsoccer", "args": ["-data", "/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `find_matches` | Matches by team, opponent, venue, competition, season, date range, stage/round |
| `head_to_head` | Wins/draws/goals between two teams, most recent meeting |
| `team_stats` | W/D/L, goals, points, win rate; home/away; per-competition breakdown |
| `team_profile` | Cross-file club overview: competitions, rivals, FIFA squad |
| `standings` | League table calculated from results (champion, relegation zone) |
| `knockout_bracket` | Libertadores / Copa do Brasil ties, aggregates and champion |
| `rank_teams` | Rank teams by points, goals, win rate, etc. (best home/away record) |
| `biggest_wins` | Largest winning margins |
| `league_stats` | Goals per match, home/draw/away rates; compare seasons |
| `list_derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `player_details` | Full FIFA profile and attributes of one player |
| `players_at_brazilian_clubs` | Per-club player summary linking FIFA data to match data |
| `list_teams`, `dataset_info` | Discover team names and data coverage |

### Files

- `normalize.go` - team name, competition and date normalization
- `data.go` - CSV loading, team identity resolution, de-duplication across files
- `query.go` - query engine (filters, records, standings, rankings, brackets, players)
- `tools.go` - MCP tool definitions and text formatting
- `mcp.go`, `main.go` - JSON-RPC/stdio server and CLI
- `soccer_test.go` - Given/When/Then scenarios, including 28 sample questions

### Behaviour worth knowing

- **Team names**: accents, case, state suffixes (`Palmeiras-SP`, `Palmeiras - SP`, `America MG`),
  club affixes (`EC Bahia`, `São Paulo FC`) and common long names all resolve to one team, while
  clubs that share a name in different states (Atlético-MG/GO, Santos-SP/AP) stay separate.
- **No double counting**: the same match often appears in several files. Each competition-season
  is read from one preferred file (the one with complete results); pass `dataset` to query a
  specific file, e.g. `extended` for corners and shots.
- **Calculated, not official**: standings come purely from match results, so points deductions
  are not reflected. Knockout ties level on aggregate are reported as undecidable (penalties and
  away goals are not in the data). The last seasons are incomplete in the source files
  (2022 and 2023 Serie A each miss a match), so no champion is declared for them.
- **FIFA data limits**: only some Brazilian clubs are in the FIFA file (no Flamengo, Palmeiras,
  Corinthians or São Paulo), and players at Brazilian clubs mostly have generated names, so
  e.g. "Gabriel Barbosa" is not found.
