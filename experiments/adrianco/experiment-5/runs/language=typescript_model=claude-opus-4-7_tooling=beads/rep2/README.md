# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that exposes the Brazilian soccer Kaggle
datasets in `data/kaggle/` as a typed query interface. Written in TypeScript
against `@modelcontextprotocol/sdk`, using `vitest` for BDD-style tests.

## Specification
TASK.md (originally brazilian-soccer-mcp-guide.md)

## Quick start

```sh
npm install
npm run build        # compiles TS -> dist/
npm test             # runs vitest suite (37 BDD tests)
npm start            # launches the MCP server over stdio
```

The server reads all six CSV files at startup (~24k matches, ~18k players) and
exposes 18 tools covering matches, teams, players, competitions, and aggregate
statistics. See `src/server.ts` for the tool catalog.

## Tools exposed

| Tool | Purpose |
|------|---------|
| `find_matches` | Filter matches by team, opponent, competition, season, date range |
| `team_stats` | W/D/L, goals for/against, points for a team & filter |
| `head_to_head` | Head-to-head summary between two teams |
| `last_match_between` | Most recent encounter between two teams |
| `team_competitions` | Competitions a team has played in |
| `team_recent_matches` | Last N matches for a team |
| `list_teams` | All distinct team names |
| `find_players` | FIFA player search by name/nationality/club/position |
| `top_brazilian_players` | Top-N Brazilian players by Overall rating |
| `standings` | Final-table standings for a competition+season |
| `champion` | Top team for a competition+season |
| `relegated` | Bottom-N for a competition+season |
| `list_competitions` | Distinct competition labels in the data |
| `list_seasons` | Seasons present (optionally per competition) |
| `aggregate_stats` | Avg goals/match, home/away/draw rates |
| `biggest_wins` | Largest goal-margin matches |
| `top_scoring_teams` | Teams ranked by goals scored |
| `best_record` | Best home or away record |

## Implementation notes

- **Team name normalization** (`src/normalize.ts`) strips diacritics, state
  suffixes (`-SP`, `-RJ`, …), country codes (`(URU)`, `-EQU`), common
  qualifiers (`FC`, `Esporte Clube`, …), and resolves a small alias table so
  the heterogeneous CSV sources match.
- **Date parsing** (`src/dates.ts`) accepts ISO `YYYY-MM-DD`, ISO datetimes,
  and Brazilian `DD/MM/YYYY` and emits ISO.
- **Standings** are computed from match results — there is no precomputed
  table, so `standings` works for any season/competition that has match data.
- All tests use vitest with Given/When/Then style scenarios.


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
