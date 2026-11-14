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

## Implementation (C++17)

A dependency-free MCP server (stdio transport, newline-delimited JSON-RPC 2.0) that loads the six
CSV files into memory (~0.1 s) and answers questions through 13 tools.

```
src/json.hpp      minimal JSON parser/serializer
src/soccer.hpp/.cpp   CSV loading, team/date/competition normalization, query engine
src/tools.hpp/.cpp    MCP tool catalogue, answer formatting, JSON-RPC handling
src/main.cpp      server entry point
tests/test_main.cpp   BDD (Given/When/Then) scenarios run against the real data
```

### Build, test, run

```bash
cmake -S . -B build && cmake --build build
(cd build && ctest --output-on-failure)     # or ./build/soccer_tests for per-scenario output
./build/brazilian_soccer_mcp [--data DIR]   # data dir also via BRSOCCER_DATA_DIR; default data/kaggle
```

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/build/brazilian_soccer_mcp" } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, stage ("Copa do Brasil finals", "when did X last play Y?") |
| `head_to_head` | match list plus wins/draws/goals between two teams |
| `team_stats` | W/D/L, goals, win rate; home/away, per season/competition |
| `team_profile` | cross-file overview: competitions played, recent matches, FIFA squad |
| `standings` | league table calculated from results; champion and relegation zone |
| `rank_teams` | best home/away record, most goals, etc. |
| `competition_stats` | goals per match, home/draw/away rates |
| `biggest_wins` | largest victory margins |
| `derbies` | matches between traditional rivals |
| `compare_seasons` | two seasons side by side |
| `search_players` | FIFA players by name, nationality, club, position (code or group) |
| `players_by_club` | player counts and average rating per club |
| `dataset_info` | rows per file, competitions and seasons covered |

### Data handling notes

- **Team names** are normalized to one key per club: state suffixes (`Palmeiras-SP`, `Flamengo - RJ`,
  `Gremio RS`), accents, club tokens (`EC`, `FC`) and full names (`Atlético Mineiro`, `Vasco da Gama`,
  `Sport Club do Recife`) all collapse; namesakes from other states stay separate (`Flamengo-PI`, `Botafogo-PB`).
- **Duplicates**: the same fixture often appears in up to three files. Rows with the same competition,
  home and away team within one day are merged into one match (7,142 rows merged, 16,811 unique matches),
  combining score, round, stadium and corner/shot statistics. Missing (`NA`) scores are filled from another file when available.
- Matches without a result are listed but excluded from all statistics.
- One Libertadores row (2022 final) has no date, score or season and is skipped.
- Seasons for `BR-Football-Dataset.csv` rows found in no other file are taken from the match year.
- Standings use points, wins, goal difference, goals for; off-field point deductions are not in the data.
  Relegation is flagged as the bottom four, which is not the actual rule for 2003–2005.
- Figures reflect the provided files, which occasionally differ from official records.
- The FIFA file contains no players for some clubs (e.g. Flamengo, Palmeiras, Corinthians); such queries return an explicit "not found".
