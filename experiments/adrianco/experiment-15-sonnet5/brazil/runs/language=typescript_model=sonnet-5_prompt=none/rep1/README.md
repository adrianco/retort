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

A TypeScript MCP server (`@modelcontextprotocol/sdk`) implementing the spec in `TASK.md`. It loads
all six CSVs into memory (no database) and exposes 12 MCP tools for querying matches, teams,
competitions, statistics and FIFA player data.

### Layout

- `src/types.ts` - shared `Match`/`Player`/`TeamKey` types
- `src/normalize.ts` - team name normalization (state-suffix parsing, accent/case folding) and
  flexible date parsing (ISO and `DD/MM/YYYY`)
- `src/dataLoader.ts` - CSV parsing and in-memory dataset assembly, including cross-dataset dedup
- `src/queries/` - `matchQueries`, `teamQueries`, `competitionQueries`, `statsQueries`, `playerQueries`
- `src/server.ts` - MCP tool registration (`find_matches`, `head_to_head`, `team_record`,
  `team_competitions`, `standings`, `list_competitions`, `average_goals`, `biggest_wins`,
  `best_venue_record`, `search_players`, `players_by_club`, `brazilian_players_by_club`)
- `src/index.ts` - stdio entry point

### Data quality decisions

- **Team names**: normalized by stripping a trailing state/country code (`Palmeiras-SP`,
  `Botafogo RJ`, `América - MG`) into a base name + code, then comparing accent/case-insensitively.
  A query with no state (`"Flamengo"`) matches any candidate with that base name; a query with an
  explicit, different state (`Atletico-GO` vs `Atletico-MG`) is treated as a different club.
- **Brasileirao overlap**: `Brasileirao_Matches.csv` (2012-2022) and `novo_campeonato_brasileiro.csv`
  (2003-2019) describe the same competition. The historical file is only used to fill in seasons
  (2003-2011) the primary file doesn't cover, avoiding double-counted matches in standings/records.
- **BR-Football overlap**: `BR-Football-Dataset.csv` also contains "Serie A"/"Copa do Brasil" rows
  that duplicate the dedicated datasets for the same seasons. Those are dropped; its unique
  contributions (Serie B, Serie C, extra stats, and any season not covered elsewhere) are kept.

### Running

```bash
npm install
npm run build   # compiles src/ -> dist/
npm start        # runs the MCP server over stdio
npm test         # vitest, 49 tests covering normalization + every query module
```

To connect from an MCP client (e.g. Claude Desktop), point it at `node dist/index.js` in this
directory after running `npm run build`.
