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

A TypeScript MCP (Model Context Protocol) server implementing the spec, built with the
[`@modelcontextprotocol/sdk`](https://modelcontextprotocol.io). It loads all six CSVs into an
in-memory knowledge store at startup and exposes 13 MCP tools an LLM can call to answer natural
language questions about Brazilian soccer matches, teams, players, and competitions.

### Run it

```bash
npm install
npm run build
npm start          # runs dist/index.js as an MCP server over stdio
# or, for development without a build step:
npm run dev
npm test           # 65 BDD-style vitest specs
```

Point any MCP-compatible client (Claude Desktop, etc.) at `node dist/index.js` in this directory.

### Architecture

- `src/data/normalize.ts` — normalizes team names across datasets (strips Brazilian-state/country
  suffixes like `-SP`/`-URU`, removes parentheticals, folds diacritics, and applies a curated alias
  table for major clubs, e.g. "Atlético-MG" and "Athletico-PR" resolve to two *different* clubs
  while "Sao Paulo"/"São Paulo"/"São Paulo FC" resolve to the *same* one) and parses the three date
  formats present in the data (ISO, ISO+time, `DD/MM/YYYY`).
- `src/data/loader.ts` / `src/data/store.ts` — parses the CSVs (UTF-8/BOM aware) into a unified
  `Match`/`Player` model and builds lookup indices by team and club.
- `src/queries/*.ts` — match search, head-to-head, team records/rankings, player search,
  calculated league standings, and statistical analysis (goals per match, home/away win rates,
  biggest wins), all operating on the in-memory store.
- `src/server.ts` / `src/index.ts` — registers each query as an MCP tool and serves them over
  stdio.

### Data quality handling

- **Overlapping sources**: `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv` both
  independently cover full 2012-2019 Brasileirão seasons, and `BR-Football-Dataset.csv` separately
  duplicates several Brasileirão and Copa do Brasil seasons. Naively concatenating all five match
  files roughly doubled several seasons' match counts and skewed every derived statistic. Each
  competition has one designated primary source per season; overlapping seasons from secondary
  sources are skipped at load time (see `SoccerDataStore` in `src/data/store.ts`), so e.g. the
  calculated 2019 Brasileirão standings match the real final table (Flamengo champions, 90 pts).
- **Team name variants** are normalized as described above so a query for "Flamengo" finds matches
  recorded as "Flamengo-RJ", "Clube de Regatas do Flamengo", etc.
- **Missing/unplayed fixtures**: a handful of rows have `NA` scores or dates (e.g. `Brasileirao_Matches.csv`'s
  2022 season was captured before it finished). These rows are kept (so the fixture list is
  complete) but excluded from computed records/statistics, which only count matches with a known
  result.
- **Known coverage gaps**: `fifa_data.csv` is a single-season FIFA snapshot and doesn't include
  every Brazilian club or player (e.g. no Flamengo squad, no player named "Gabriel Barbosa" under
  that exact name) — player queries for those return no results, which is a limitation of the
  provided dataset rather than the query logic.
- Relegation isn't directly encoded in the data (the number of relegated teams changed across
  years), so `relegation_zone` returns the bottom N calculated table positions as a documented
  proxy rather than claiming to be the official outcome.

### MCP tools

`search_matches`, `head_to_head`, `most_recent_match`, `team_record`, `team_competitions`,
`rank_teams`, `search_players`, `brazilian_players_by_club`, `standings`, `relegation_zone`,
`seasons_for_competition`, `goal_stats`, `biggest_wins`.
