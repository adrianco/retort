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

## Implementation (Clojure)

An MCP server (JSON-RPC 2.0 over stdio, newline-delimited) that loads the six
CSV files into memory and answers questions through tools.

```bash
clojure -M:run     # start the MCP server on stdin/stdout
clojure -M:test    # run the test suite
```

MCP client configuration (run from this directory, or set `BRSOCCER_DATA_DIR`
to the absolute path of `data/kaggle`):

```json
{"mcpServers": {"brazilian-soccer": {"command": "clojure", "args": ["-M:run"]}}}
```

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, venue, competition, season, date range, round, stage |
| `head_to_head` | all meetings of two teams with wins/draws/goals |
| `team_stats` | W/D/L, goals, win rate by season / competition / home-away |
| `standings` | league table calculated from results, champion, relegation |
| `rank_teams` | best home/away record, most goals, etc. |
| `competition_stats` | goals per match, home/draw/away rates |
| `biggest_wins` | largest winning margins |
| `team_competitions` | competitions and seasons a team appears in |
| `derbies` | matches between traditional rivals |
| `search_players`, `player_details` | FIFA players by name, nationality, club, position, rating |
| `brazilian_club_squads`, `team_profile` | player data joined with match data |
| `list_competitions` | what the dataset covers |

Layout: `src/brsoccer/names.clj` (team/competition name normalisation),
`data.clj` (CSV loading and cross-file merge), `query.clj` (queries),
`format.clj` (text answers), `server.clj` (MCP protocol and tools); tests in
`test/brsoccer/`.

Notes on the data:

- The same fixture often appears in two or three files; such rows are merged
  into one match (same competition and home/away teams within 3 days), so
  statistics are not double counted. 23,954 match rows become 16,750 matches.
- Rows without a score (unplayed fixtures) and two corrupt cup rows listing a
  team against itself are skipped.
- `BR-Football-Dataset.csv` has no season column; the season is the year of
  the match date, except that games before 2021-03-08 belong to the delayed
  2020 season.
- Standings are computed from results only. A champion and relegation zone
  are only named when the season is complete in the data (2023 is three
  matches short).
- The FIFA file has no Flamengo, Palmeiras, Corinthians or São Paulo squads,
  and the players of the Brazilian clubs it does include carry FIFA's
  unlicensed placeholder names.
