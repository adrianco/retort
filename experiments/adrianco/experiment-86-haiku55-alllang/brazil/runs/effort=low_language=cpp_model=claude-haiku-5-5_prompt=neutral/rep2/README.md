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

## MCP server (C++17)

A Model Context Protocol server that answers questions about Brazilian soccer from the CSVs in `data/kaggle/`.
It speaks JSON-RPC 2.0 over stdio, has no third-party dependencies, and loads all six datasets at startup.

### Build and test

```sh
cmake -S . -B build
cmake --build build
./build/soccer_tests          # or: cd build && ctest
```

### Run

```sh
./build/brazilian_soccer_mcp [--data-dir data/kaggle]
```

Register it with an MCP client by pointing the client's stdio command at the binary.

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range or round |
| `head_to_head` | Record between two teams, with their matches |
| `team_record` | Wins, draws, losses and goals for a team, optionally by competition, season or venue |
| `standings` | League table for a competition and season, calculated from results |
| `league_stats` | Goals per match and home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `search_teams` | Exact team-name spelling from a partial name |
| `search_players` | FIFA players by name, nationality, club, position or rating |
| `club_summary` | Squad size and average rating per club |

### Data handling

- **Team names** are normalized: state suffixes (`Palmeiras-SP`, `Vasco Da Gama RJ`), parenthetical notes and
  accents are removed, and known aliases (`Sport Club Corinthians Paulista`, `Athletico-PR`) map to one club.
  A bare name such as `Flamengo` matches every state; a name with a state only matches that state.
- **Dates** accept `YYYY-MM-DD`, `DD/MM/YYYY` and timestamps.
- **Overlapping files:** the Brasileirão appears in three files, and the BR-Football file's 2019 season disagrees with
  the other files on dates and scores. For each competition and season, only the most complete file is used, so
  no season is counted twice. Load diagnostics are printed to stderr at startup.

### Known data limitations

- `BR-Football-Dataset.csv` has 377 Série A rows for 2023 (a full season has 380), so 2023 tables are incomplete.
- Its 2020 Série A is partial (264 rows), and its 2021 Série A has 491 rows, more than one season.
- The FIFA file is the FIFA 19 edition: it has no players for Flamengo and no "Gabriel Barbosa".
- Copa do Brasil finals are not labelled in the data; the last round of each season is the final.
