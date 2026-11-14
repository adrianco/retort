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

## Java MCP server

A stdio MCP server (JSON-RPC 2.0, newline-delimited) that loads the six CSV files into memory and answers
questions through 15 tools. Requires Java 17+ and Maven.

```bash
mvn clean package                                   # builds and runs the 52 tests
java -jar target/brazilian-soccer-mcp-1.0.0.jar     # serves on stdin/stdout; data from ./data/kaggle
```

The data directory can be given as the first argument or in `BRAZILIAN_SOCCER_DATA_DIR`.
Example client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "java",
  "args": ["-jar", "/path/to/target/brazilian-soccer-mcp-1.0.0.jar", "/path/to/data/kaggle"]}}}
```

| Tool | Answers |
|------|---------|
| `find_matches` | Matches by team, opponent, venue, competition, season, date range, stage, round, source file |
| `head_to_head` | Two-team comparison: wins, draws, goals, home/away, per competition |
| `team_stats` | W/D/L, goals and win rate for a team (season / competition / home-away) |
| `team_profile` | Competitions played, overall record, rivals, FIFA squad (cross-file) |
| `team_rankings` | Best home/away record, most goals, etc. |
| `standings` | League table calculated from results, champion and relegated teams |
| `competition_bracket` | Libertadores / Copa do Brasil knockout rounds with aggregates |
| `match_statistics` | Average goals, home/draw/away rates, goals per season |
| `compare_seasons` | Two seasons side by side |
| `biggest_wins` | Largest winning margins |
| `derbies` | Matches between traditional rivals |
| `search_players`, `player_details`, `players_by_club` | FIFA player database |
| `dataset_info` | Files, coverage, limitations |

Implementation notes (code in `src/main/java/br/soccer/mcp`, tests in `src/test/java/br/soccer/mcp`):

- **Team names** are normalised to one key per club (`Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras`; `Atletico Mineiro` =
  `Atlético-MG`); the state is kept only where clubs share a name. Small clubs spelled very differently between files
  (e.g. `Atletico Acreano` / `Atlético - AC`) are not merged.
- **Overlapping files**: the same season can appear in up to three files, so for each competition and season the file
  with the most scored matches is used; pass `source` to `find_matches` to query one file directly.
- **Data limits**: standings ignore points deductions; Serie A 2022 and 2023 and all Serie B/C seasons are incomplete
  in the data, so no champion is declared for them; there is no goal-scorer data; the FIFA file contains 15 Brazilian
  clubs (not Flamengo, Palmeiras, Corinthians or São Paulo); one Libertadores row with no date or season is dropped.
