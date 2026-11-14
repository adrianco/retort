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

## Implementation (TypeScript MCP server)

An MCP server (stdio transport) that loads the six CSV files into memory and exposes
17 tools for match, team, player, competition and statistical queries.

```bash
npm install
npm run build      # compiles src/ to dist/
npm test           # BDD-style vitest suites (Feature / Scenario, Given-When-Then)
npm start          # runs the MCP server on stdio
```

Register it with an MCP client, e.g. `claude mcp add brazilian-soccer -- node /path/to/dist/index.js`.
Set `BRAZILIAN_SOCCER_DATA_DIR` to load the CSV files from somewhere other than `data/kaggle`.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, stage/round ("Find all Copa do Brasil finals") |
| `head_to_head` | Two-team comparison with wins, draws, goals and recent meetings |
| `team_stats` | W/D/L, goals, win rate; by season, competition, home/away |
| `team_profile` | Competitions and seasons played, name variants, rivals, FIFA squad (cross-file) |
| `list_teams` | Teams in the match data |
| `standings` | League table calculated from results, champion and bottom four |
| `cup_summary` | Copa do Brasil / Libertadores bracket with aggregate scores and winner |
| `competition_stats` | Goals per match, home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `rank_teams` | Best home/away record, most goals, etc. |
| `compare_seasons` | Two seasons side by side |
| `find_derbies` | Matches between traditional rivals |
| `extended_match_stats` | Corners, shots and attacks from `BR-Football-Dataset.csv` |
| `search_players` | FIFA players by name, nationality, club, position |
| `player_details` | One player's full profile |
| `club_player_summary` | Player counts and average rating per club |
| `dataset_info` | Files, row counts, competitions and seasons covered |

### Layout

- `src/normalize.ts` – team-name, date, number and competition normalisation
- `src/csv.ts` – CSV parser
- `src/data.ts` – loaders for the six files and de-duplication across overlapping files
- `src/queries.ts` – query layer (`SoccerDB`)
- `src/server.ts` – MCP tool definitions and text formatting
- `src/index.ts` – stdio entry point
- `tests/` – normalisation, query and end-to-end MCP tests (including 28 sample questions)

### Data notes

- Série A seasons appear in up to three files. Aggregates use one file per season:
  `novo_campeonato_brasileiro` (2003-2011), `Brasileirao_Matches` (2012-2022) and
  `BR-Football-Dataset` (2023). Copa do Brasil uses `Brazilian_Cup_Matches` (2012-2021) and
  `BR-Football-Dataset` afterwards. Any tool's `source` argument queries a single file instead.
- `BR-Football-Dataset.csv` has no season column, so its season is the calendar year of the match.
- Standings come purely from results: points deductions are not in the data, and a champion is only
  declared when every team has played a full double round-robin (2022 and 2023 are incomplete in the files).
- Cup ties level on aggregate are reported as undecided, because penalties and away-goal outcomes are not in the data.
- `fifa_data.csv` (FIFA 19) has no squads for Flamengo, Palmeiras, Corinthians, São Paulo and several other Brazilian clubs.
