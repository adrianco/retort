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

An MCP server written in Objective-C using only Foundation (no third-party
dependencies). It loads the six CSV files into memory at start-up (about 0.4s)
and speaks JSON-RPC 2.0 over stdio, one message per line.

### Build, test, run

```sh
make            # builds build/brazilian-soccer-mcp
make test       # builds and runs the BDD suite against data/kaggle
build/brazilian-soccer-mcp --data data/kaggle          # serve MCP on stdin/stdout
build/brazilian-soccer-mcp --call standings '{"season":2019}'   # one-off tool call
build/brazilian-soccer-mcp --list-tools
```

Requires macOS with the Xcode command line tools (`clang`). The data directory is
taken from `--data`, then `$BRSOCCER_DATA_DIR`, then `./data/kaggle`.

MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/build/brazilian-soccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Tools

| Tool | Answers |
|------|---------|
| `find_matches` | Matches by team, opponent, venue, competition, season, date range, stage/round |
| `head_to_head` | Record between two teams plus recent meetings |
| `team_stats` | W/D/L, goals, win rate, home/away split, per-competition breakdown |
| `team_competitions` | Competitions and seasons a team appears in |
| `team_profile` | Match record plus the club's FIFA players (cross-file) |
| `standings` | League table calculated from results, champion and relegation zone |
| `competition_bracket` | Libertadores / Copa do Brasil knockout results |
| `league_stats` | Goals per match, home/draw/away rates |
| `biggest_wins` | Largest victories |
| `team_rankings` | Best home/away records, most goals, etc. |
| `compare_seasons` | Two seasons side by side |
| `derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `player_details` | Full player profile |
| `club_player_summary` | Players of a nationality grouped by club |
| `dataset_info` | Coverage of the loaded data |

### Layout

- `src/BSCSV` - CSV reader (quotes, BOM, CRLF, UTF-8)
- `src/BSTeamNames` - team name normalisation and derby list
- `src/BSDataStore` - loading, date handling, merging of fixtures found in several files
- `src/BSQueryEngine` - match search, records, tables, aggregates, player search
- `src/BSTools` - MCP tool schemas, argument validation, text answers
- `src/BSMCPServer`, `src/main.m` - JSON-RPC/stdio server and CLI
- `tests/BSTests.m` - Given/When/Then scenarios run against the real data

### Data notes

- The same fixture often appears in two or three files (e.g. Serie A 2012-2019).
  These are merged into one match (keeping round, stadium and shot/corner
  statistics from whichever file has them), so statistics are not double counted.
- `BR-Football-Dataset.csv` has no season column; the season is the calendar year,
  except that early-2021 matches belong to the delayed 2020 editions.
- That file also contains a few state-league fixtures mislabelled as Serie A/B;
  clubs with only such stray matches are left out of league tables.
- The 2023 Serie A data is missing three matches, so `standings` shows the table
  with a warning instead of naming a champion.
- Copa do Brasil finals are inferred as the last round of each season in
  `Brazilian_Cup_Matches.csv`; this identifies the finals of the 2012-2020 seasons only.
- Flamengo, Corinthians, Palmeiras, São Paulo and some other Brazilian clubs are
  not in the FIFA file, and the Brazilian clubs that are have generated player names.
