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

## Implementation (TypeScript)

An MCP server (stdio) that loads the six CSV files into memory and exposes them as tools.

```bash
npm install
npm run build      # tsc -> dist/
npm test           # vitest, BDD-style scenarios in tests/
npm start          # run the server on stdio
```

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "node", "args": ["/path/to/repo/dist/server.js"] } } }
```

The data directory defaults to `data/kaggle` next to the build; override with `BRAZILIAN_SOCCER_DATA_DIR`.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team / opponent / home / away, competition, season, date range, stage (e.g. finals) |
| `head_to_head` | Meetings and win/draw/goal totals between two teams |
| `team_stats` | W/D/L, goals, points, win rate for a team (season, competition, home/away) |
| `team_overview` | Competitions and seasons a team played, plus its FIFA squad (cross-file) |
| `standings` | League table calculated from results, with champion and relegation zone |
| `competition_knockout` | Cup bracket by stage and the winner of the final |
| `rank_teams` | Best home/away records, most goals, most points |
| `league_stats` | Goals per match, home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `compare_seasons` | Two seasons side by side |
| `find_derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `player_profile` | One player's ratings and skills, plus their club's latest results |
| `brazilian_club_squads` | Brazilian clubs in the FIFA data with squad size and average rating |
| `dataset_info` | What is loaded: rows per file, competitions, seasons |

### Layout

- `src/csv.ts` – CSV parser
- `src/teams.ts` – team name normalisation ("Palmeiras-SP" = "Palmeiras"; "Botafogo-PB" ≠ "Botafogo")
- `src/data.ts` – loading, date parsing, merging the same fixture across files
- `src/queries.ts` – query layer (`SoccerKB`)
- `src/tools.ts` / `src/server.ts` – tool definitions and the MCP server
- `tests/` – scenarios for normalisation, data loading, queries, the MCP protocol, 29 sample questions and response times

### Data handling notes

- The three files covering Série A overlap (2012-2022). A fixture found in several files is merged into one
  match that keeps the stadium, round and shot/corner statistics; every 2006-2022 season has exactly 380 matches.
- `BR-Football-Dataset.csv` has no season column: the year of the date is used, except that games up to
  7 March 2021 belong to the delayed 2020 season.
- Rows without a score (unplayed, "NA", "-"), rows where a team plays itself, and a handful of stray
  "Serie A" rows in the extended file that contradict the dedicated Série A files are dropped.
- The Copa do Brasil files have no stage; the final is taken to be the last tie of each season.
- Standings ignore points deductions, which are not in the data.
- The FIFA file is FIFA 19 and only contains licensed Brazilian clubs (no Flamengo, Palmeiras, Corinthians
  or São Paulo; real players such as Gabriel Barbosa are missing). Queries for those return "not found".
- Some small clubs are spelled too differently between the cup file and the extended file to be matched,
  so a few early-round cup games may appear twice.
