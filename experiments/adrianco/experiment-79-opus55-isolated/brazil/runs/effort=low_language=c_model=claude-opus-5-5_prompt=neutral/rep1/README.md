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

## Implementation (C)

A dependency-free MCP server written in C11 (`src/`), speaking JSON-RPC 2.0 over stdio
(one message per line). All six CSV files are loaded into memory at start-up (~40 ms).

```sh
make            # builds ./brsoccer-mcp
make test       # BDD-style tests (tests/test_soccer.c) + stdio end-to-end test
./brsoccer-mcp --data data/kaggle                      # run as an MCP server
./brsoccer-mcp --call standings '{"season":2019}'      # one-off tool call from the shell
```

The data directory is taken from `--data`, then `$BRSOCCER_DATA_DIR`, then `./data/kaggle`.
Example MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brsoccer-mcp", "args": ["--data", "/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, stage, round |
| `head_to_head` | Two-team comparison with home/away and per-competition breakdown |
| `team_stats` | W/D/L, goals, win rate for a team (season / competition / home / away) |
| `team_competitions` | Competitions and seasons a team appears in |
| `team_profile` | Cross-file profile: match record, rivals, FIFA squad |
| `standings` | League table computed from results (champion, relegation) or cup bracket |
| `team_rankings` | Rank teams by win rate, points, goals, ... (home/away/overall) |
| `competition_stats` | Goals per match, home/draw/away rates, corners, shots |
| `compare_seasons` | Side-by-side statistics and champions of two seasons |
| `biggest_wins` | Largest victories by margin |
| `derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `player_details` | Full profile of one player |
| `players_by_club` | Players of a nationality grouped by club |
| `dataset_info` | Loaded files, match counts, competitions and seasons |

### Notes on the data

- Team names are normalized (accents, state suffixes such as `Palmeiras-SP`, aliases such as
  `Atlético Mineiro`), while homonyms from different states (`Botafogo-PB`) stay distinct.
- The files overlap (three carry Serie A, two carry Copa do Brasil). The same fixture within
  two days is merged into one match, keeping the file with the richest data as primary.
- Standings are computed from results only, so they ignore official points deductions.
- The FIFA file does not contain every Brazilian club (no Flamengo, Palmeiras, Corinthians,
  São Paulo), and some players such as Gabriel Barbosa are absent; the server says so.
