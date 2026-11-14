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

## Implementation (Objective-C)

An MCP server written in Objective-C (Foundation only, no third-party dependencies) that loads
the six CSV files into memory and answers questions through MCP tools over stdio
(newline-delimited JSON-RPC 2.0).

### Build, test, run

Requires macOS with the Xcode command line tools (`clang`).

```sh
make            # builds build/brazilian-soccer-mcp
make test       # builds and runs the BDD-style suite against data/kaggle
build/brazilian-soccer-mcp --data-dir data/kaggle                   # serve MCP on stdin/stdout
build/brazilian-soccer-mcp --call standings '{"season":2019}'       # one-shot tool call for debugging
```

The data directory is found from `--data-dir`, then `BRAZILIAN_SOCCER_DATA_DIR`, then `./data/kaggle`
(relative to the working directory or to the binary). Example MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {
  "command": "/path/to/build/brazilian-soccer-mcp",
  "args": ["--data-dir", "/path/to/data/kaggle"]}}}
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, round, stage (e.g. cup finals) |
| `head_to_head` | Two-team comparison, most recent meeting |
| `team_stats` | W/D/L, goals, win rate; by season, competition, home/away |
| `team_profile` | Cross-file: competitions played, overall record, FIFA squad |
| `standings` | League table computed from results; champion and bottom four |
| `cup_bracket` | Libertadores / Copa do Brasil stages and champion |
| `team_rankings` | Best home/away record, most goals, points, etc. |
| `biggest_wins` | Largest winning margins |
| `league_statistics` | Goals per match, home/draw/away rates, corners and shots |
| `compare_seasons` | Two seasons side by side |
| `find_derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position |
| `player_details` | One player's full profile |
| `players_by_club` | Players of a nationality grouped by club |
| `dataset_info` | What is loaded |

### Layout

- `src/BSCSV` - CSV reader (quotes, BOM, CRLF, UTF-8)
- `src/BSTeamNames` - team name normalisation and derby list
- `src/BSDataStore` - loading, cross-file de-duplication, queries
- `src/BSTools` - tool schemas and text answers
- `src/BSMCPServer`, `src/main.m` - JSON-RPC / stdio
- `tests/BSTests.m` - Given/When/Then scenarios (plain executable, no XCTest needed)

### Data handling notes

- **Overlapping files are merged.** The same Serie A fixture can appear in three files; it is
  stored once (16,790 unique matches from 23,954 rows) and remembers its sources. Where one file
  has no score (81 rows of 2022 in `Brasileirao_Matches.csv`) the score comes from another file.
- **Team names** are reduced to one key per club: state suffixes, accents, "FC/EC" tokens and
  official long names are handled; namesakes (Flamengo-PI, Botafogo-PB, Atlético-GO/MG) stay separate.
- **Seasons** for `BR-Football-Dataset.csv` are derived from the date; league games in January or
  February count for the previous season (the 2020 season ended in February 2021).
- **Copa do Brasil stages** are inferred from round numbers in `Brazilian_Cup_Matches.csv`
  (2012-2020). The 2021-2023 cup matches come only from the extended-stats file, which has no
  round information, so their finals are not labelled.
- Some lower-division clubs are spelled too differently between the cup files to be matched, so a
  small number of cup matches may be present twice.
- Standings are computed from results only (no points deductions); relegation is shown as the
  bottom four. In 2023 the source data is missing three Serie A matches.
- The FIFA file does not contain Flamengo, Palmeiras, Corinthians or São Paulo squads, and many
  players at the Brazilian clubs it does contain have generic (unlicensed) names. Player queries for
  those clubs return an explanatory message.
- No top-scorer tool: none of the files record who scored.
