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

A dependency-free Go MCP server (`brsoccer-mcp`, standard library only) that loads the six CSV files into memory
and exposes them as MCP tools over stdio (JSON-RPC 2.0, newline-delimited).

### Build, test, run

```bash
go build -o brsoccer-mcp .
go test ./...                       # BDD-style scenarios against the real data
./brsoccer-mcp                      # serve MCP on stdin/stdout (reads data/kaggle)
./brsoccer-mcp -data /path/to/csvs  # or set BRSOCCER_DATA_DIR
./brsoccer-mcp -call standings -args '{"season":2019}'   # run one tool from the shell
```

MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brsoccer-mcp", "args": ["-data", "/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, cup stage (`stage=final`) |
| `head_to_head` | two-team comparison: wins/draws/goals, per competition, latest meeting |
| `team_stats` | W/D/L, goals, win rate, home/away split, per competition, corner/shot averages |
| `team_profile` | cross-file overview: competitions played, rivals, recent matches, FIFA squad |
| `standings` | league table calculated from results; champion and relegated teams |
| `competition_bracket` | Libertadores / Copa do Brasil knockout rounds and winner |
| `competition_stats` | goals per match, home/draw/away rates, corners |
| `compare_seasons` | two seasons side by side |
| `team_rankings` | best home/away record, most goals, etc. |
| `biggest_wins` | largest margins of victory |
| `derbies` | matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position (codes or groups), rating |
| `player_details` | full player profile and skill ratings |
| `players_by_club` | players grouped by club (e.g. Brazilians at Brazilian clubs) |
| `dataset_info` | coverage of the loaded data |

### Files

- `main.go` – entry point and flags
- `mcp.go` – MCP/JSON-RPC protocol handling
- `tools.go` – tool definitions, argument validation, text formatting
- `queries.go` – filters, records, standings, rankings, player search
- `data.go` – CSV loading, date/score parsing, merging of overlapping sources
- `normalize.go` – team name normalisation
- `soccer_test.go` – Given/When/Then scenarios, including 27 sample questions with response-time budgets

### Data handling notes

- **Team names** are reduced to an accent-free base name plus state (`Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras`,
  `Sao Paulo`/`São Paulo`, `Atletico Mineiro`/`Atlético-MG`, `Sport Club Corinthians Paulista` ...). Namesakes stay
  separate (Atlético-MG / Athletico-PR / Atlético-GO, Botafogo / Botafogo-PB / Botafogo-SP, River Plate / River Plate-URU).
- **Overlapping sources** are merged rather than double counted: the three Brasileirão files and the two Copa do Brasil
  files describe many of the same matches. A merged match keeps the round from one file, the stadium from another and
  corner/shot statistics from BR-Football-Dataset. 16,7xx unique matches remain from 23,9xx rows (`dataset_info` shows exact numbers).
- **Unplayed fixtures** (scores `NA` or `-`) are skipped.
- **Seasons**: the 2020 season, which ended in early 2021, is assigned to 2020 also where the source has only a date.
- **Standings** use 3 points per win with ties broken by wins, goal difference, goals scored. They are calculated only
  from the matches present: points deductions are unknown, and a season that is incomplete in the data (e.g. 2023,
  377 of 380 matches) is labelled partial instead of naming a champion.
- **Known limits of the data**: the FIFA file (FIFA 19) contains only 15 Brazilian clubs — Flamengo, Palmeiras,
  Corinthians and São Paulo are absent, and most players at Brazilian clubs have fictitious names — so questions such
  as "players at Flamengo" return an explanation and the list of clubs available. There is no goal-scorer data, so
  "top scorers" are answered per team, not per player. Copa do Brasil rounds (and therefore finals) are only known for
  2012–2021; two-legged finals level on aggregate are reported as undetermined because penalties are not in the data.
  A handful of obscure lower-division clubs spelled differently across files may remain unmerged.
