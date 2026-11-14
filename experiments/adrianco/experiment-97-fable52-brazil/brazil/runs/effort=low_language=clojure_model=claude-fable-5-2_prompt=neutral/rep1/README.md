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

---

# Implementation: Brazilian Soccer MCP server (Clojure)

An MCP server (JSON-RPC 2.0 over stdio) that loads the six CSV files into memory and
exposes 17 query tools. No database or network access is needed.

## Run

Requires Java and the Clojure CLI.

```bash
clojure -M:test                 # run the test suite
clojure -M:run                  # start the MCP server on stdio
clojure -M:run tools            # list the tools
clojure -M:run call standings '{"season": 2019}'   # call one tool from the shell
```

MCP client configuration (run from this directory, or set `BRSOCCER_DATA_DIR` to the
folder holding the CSV files):

```json
{"mcpServers": {"brazilian-soccer": {"command": "clojure", "args": ["-M:run"],
                                     "cwd": "/path/to/this/repo"}}}
```

## Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, stage/round |
| `head_to_head` | Two-team comparison: wins, draws, goals, home records, recent meetings |
| `team_stats` | W/D/L, goals, win rate; by season, competition, home/away |
| `team_overview` | Competitions played, records per competition, latest matches, FIFA squad |
| `team_season_trend` | Season-by-season record and finishing position |
| `standings` | League table calculated from results, with champion and relegated clubs |
| `competition_bracket` | Copa do Brasil / Libertadores knockout ties, aggregates, champion |
| `match_statistics` | Goals per match, home/draw/away rates, corners and shots where available |
| `compare_seasons` | Side-by-side season aggregates |
| `team_rankings` | Best home/away record, most goals, etc. |
| `biggest_wins` | Largest winning margins |
| `find_derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating, age |
| `player_details` | One player's full profile |
| `brazilian_club_players` | Player count and average rating per Brazilian club |
| `list_teams` | Team-name search |
| `dataset_info` | Files loaded, coverage, limits |

## Layout

- `src/brsoccer/teams.clj` – team-name normalisation and the derby list
- `src/brsoccer/data.clj` – CSV loading, date/score parsing, cross-file de-duplication
- `src/brsoccer/queries.clj` – pure query functions
- `src/brsoccer/tools.clj` – tool schemas, argument validation, text rendering
- `src/brsoccer/mcp.clj` – JSON-RPC / MCP protocol handling
- `src/brsoccer/main.clj` – entry point
- `test/brsoccer/` – Given/When/Then scenarios with `clojure.test`

## How the data is handled

- **Team names.** Each raw name is split into a base name and a state/country suffix
  (`Palmeiras-SP`, `América - MG`, `Botafogo RJ`, `Nacional (URU)`), accents and club-type
  tokens are folded away, and an alias table covers full names (`Atlético Mineiro`,
  `Sport Club do Recife`). Namesakes stay separate (Atlético-MG / -GO, Flamengo / Flamengo-PI).
- **Duplicates.** The three Série A sources and two Copa do Brasil sources overlap. The same
  fixture in the same competition within two days is kept once (the files disagree on
  kick-off date by time zone), and corners/shots/stadium are merged into the surviving row.
  23,954 match rows become 16,784 unique matches.
- **Unplayed matches** (score `NA` or `-`) are skipped.
- **Seasons.** `BR-Football-Dataset.csv` has no season column; the year of the date is used,
  except that early-2021 matches belong to the pandemic-delayed 2020 season.
- **Players to clubs.** A FIFA club is linked to a match-data team only if the names match
  and most of its squad is Brazilian, so Portugal's Boavista FC is not Boavista-RJ.

## Known limits of the data

- Standings come from results only; tribunal point deductions are not in the data.
- Seasons that are incomplete in the files (e.g. Série A 2023 has 377 of 380 matches) get a
  table but no champion/relegation labels.
- Two-legged ties level on aggregate cannot be resolved (no penalties or away-goal data).
- No goal-scorer data, so top scorers cannot be derived.
- The FIFA file contains 15 Brazilian clubs; Flamengo, Palmeiras, Corinthians and São Paulo
  are not among them, and most players at the clubs it does have carry FIFA's generic names.
- `BR-Football-Dataset.csv` labels one 2016 Brasília v Taguatinga match as "Serie A"; it is
  kept as the file has it.
