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

An MCP server (stdio transport) that answers natural-language-style questions about Brazilian
soccer by exposing structured query tools over the six CSV files in `data/kaggle/`.

### Setup

```bash
npm install
npm run build      # compile to dist/
npm test           # Vitest suite (BDD-style Feature/Scenario tests)
npm start          # run the MCP server on stdio
```

Attach to an MCP client, e.g. Claude Code:

```bash
claude mcp add brazilian-soccer -- node /absolute/path/to/dist/index.js
```

Set `DATA_DIR` to load a different copy of the datasets.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team (home/away/any), opponent, competition, season, date range |
| `team_stats` | W/D/L, goals for/against, win rate, optionally by competition, season, venue |
| `head_to_head` | Record between two teams plus most recent meetings |
| `standings` | League table for a season, calculated from results (3 pts/win, 1 pt/draw) |
| `biggest_wins` | Largest margins of victory |
| `aggregate_stats` | Average goals per match, home/draw/away rates; season ranges |
| `search_players` | FIFA players by name, nationality, club, position, rating; sortable |
| `club_squad_summary` | Average overall per club; optionally Brazilian clubs only |

### How the data is combined

- **Competitions:** Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores are normalised
  to canonical names. Overlapping rows across files are de-duplicated on
  (season, competition, teams, score), because sources disagree on dates by a day at times.
- **Team names:** `Palmeiras-SP`, `Palmeiras`, `Sociedade Esportiva Palmeiras` and accent variants
  resolve to one key. Clubs that share a base name across states are kept apart: the most
  frequent state keeps the plain name, and others are qualified, e.g. `Botafogo (SP)`.
  Known full-name aliases live in `src/normalize.ts`.
- **Dates:** ISO, `DD/MM/YYYY`, and timestamped forms are all accepted.
- **Players:** FIFA data is joined to match data by club name, so "Brazilian clubs" means clubs
  that appear in the Brazilian match files.

### Known limitations

- Source data is incomplete for some seasons and not every player's club name matches a match-data
  team. Those players are excluded from "Brazilian clubs" summaries.
- Top scorers are not derivable from the provided data and are not implemented.
- Results come from the provided CSVs only; no live API data is used.

### Layout

- `src/normalize.ts`: team keys, state detection, accent-insensitive matching
- `src/dates.ts`, `src/csv.ts`: parsing helpers
- `src/dataset.ts`: loads and de-duplicates all six files
- `src/queries.ts`: pure query functions
- `src/format.ts`: text output for the LLM
- `src/server.ts`, `src/index.ts`: MCP server wiring and stdio entry point
- `tests/`: Feature/Scenario tests; `tests/fixtures/` builds a hand-checked dataset
