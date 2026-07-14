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

## Implementation

A TypeScript MCP (Model Context Protocol) server implementing the spec in `TASK.md`, built test-first (TDD: a failing test before each unit of implementation, then the minimum code to pass it).

### Install, build, test

```
npm install
npm run build   # compiles src/ -> dist/
npm test        # runs the vitest suite
npm start       # starts the MCP server over stdio (after build)
```

To connect it to an MCP client (e.g. Claude Desktop/Code), point the client at `node dist/index.js` in this directory. The `BRAZILIAN_SOCCER_DATA_DIR` env var can override the default `data/kaggle` location.

### Architecture

- `src/csv.ts`, `src/dates.ts`, `src/normalize.ts` — small parsing/normalization primitives (RFC4180-ish CSV, ISO/BR date formats, Brazilian team-name normalization).
- `src/dataLoader.ts` — parses each of the 6 CSVs into a shared `Match`/`Player` shape and merges them into one in-memory dataset.
- `src/matchQueries.ts`, `src/teamQueries.ts`, `src/playerQueries.ts`, `src/competitionQueries.ts`, `src/statsQueries.ts` — pure query/aggregation functions over the in-memory data (search, head-to-head, records, standings, dataset-wide stats).
- `src/tools.ts` — formats query results into the text responses the MCP tools return; `src/server.ts` registers 8 MCP tools (`search_matches`, `team_record`, `compare_teams`, `search_players`, `competition_standings`, `dataset_statistics`, `list_team_competitions`, `player_club_context`) backed by those functions; `src/index.ts` is the stdio entrypoint.

Everything (~24k matches, ~18k players) loads in well under half a second and every tool call responds in well under 100ms in testing, comfortably inside the spec's 2s/5s targets.

### Data quality notes

The datasets spell the same club differently across sources (accents, casing, `-UF` state suffixes, full vs. short names). `canonicalizeTeamNames` collapses these to one display name per club. Brazilian football also has several genuinely distinct clubs that share a short name across states (e.g. Atlético‑MG/GO/PR, Botafogo‑RJ/PB); when a name's state variants each have a non-trivial share of its matches, the loader keeps them separate as `Name-UF`; a lone stray match from an obscure homonym club is treated as noise and folds into the dominant club instead. Overlapping-source duplicates (e.g. the same season covered by both `Brasileirao_Matches.csv` and `BR-Football-Dataset.csv`) are deduplicated via `canonicalMatches` before aggregation. This is a best-effort heuristic, not authoritative club-ID resolution — for a non-commercial demo over messy public CSVs, it trades occasional edge-case ambiguity for correct results on every well-known club.
