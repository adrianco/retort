# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that answers
natural-language questions about Brazilian soccer — players, teams, matches,
competitions, and statistics — over six pre-downloaded Kaggle datasets.

Implemented in **TypeScript** against the official `@modelcontextprotocol/sdk`,
with a dependency-free CSV pipeline and a query layer that normalizes the messy,
overlapping source data into clean, queryable collections. Tested with
**BDD (Given/When/Then)** scenarios via Vitest.

---

## What was built

```
src/
  data/
    csv.ts          RFC-4180-style CSV parser (quoted fields, BOM, embedded commas)
    normalize.ts    Team-name / date / number normalization + fuzzy team matcher
    types.ts        Shared domain types (Match, Player, StandingRow, ...)
    loader.ts       Loads & unifies the 6 CSVs; canonical-source dedup; caching
  queries/
    matches.ts      Find matches (team / opponent / competition / season / dates), head-to-head
    teams.ts        Team W/D/L + goals records, competition history
    players.ts      Player search (name / nationality / club / position), club summaries
    competitions.ts Standings & champion / relegation, computed from results
    statistics.ts   Aggregates: goals/match, win rates, biggest wins, leaderboards
  format.ts         Render results into the human-readable text shown in the spec
  server.ts         MCP server: 14 tools (Zod-validated) returning text + structured JSON
  index.ts          stdio entrypoint
tests/              BDD test suites (82 tests)
features/           Gherkin feature files documenting the scenarios
```

### Key data-quality decisions

The six CSVs are heterogeneous and **overlapping**:

- **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, `São Paulo` vs
  `Sao Paulo`, full legal names (`Sport Club Corinthians Paulista`). All are
  reduced to a stable matching key. Crucially, the Brazilian state suffix is
  kept as a disambiguator so **Atlético-MG ≠ Athletico-PR**, while a stateless
  query (`"Palmeiras"`) still matches the suffixed data (`"Palmeiras-SP"`) via a
  wildcard matcher.
- **Multiple date formats** — ISO (`2023-09-24`), ISO + time
  (`2012-05-19 18:30:00`), and Brazilian `DD/MM/YYYY` are all parsed to ISO.
- **UTF-8 / accents** — handled throughout (BOM stripping, accent-insensitive
  search).
- **Overlapping coverage** — Série A 2012–2019 appears in three files and Copa
  do Brasil in two. Counting them all would triple standings and head-to-head
  numbers. The loader selects a **single canonical source per
  (competition, season)**, yielding clean non-overlapping coverage. (Verified:
  2019 Série A → 380 matches, 20 teams, Flamengo champion on 90 pts, exactly
  matching the reference answer in the spec.)

### MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team / opponent / competition / season / date range |
| `head_to_head` | Win/draw/goal record between two teams |
| `team_record` | A team's W/D/L + goals (by season / competition / venue) |
| `team_competitions` | Competitions a team has appeared in |
| `search_players` | FIFA players by name / nationality / club / position |
| `players_by_club` | Players grouped by club (count + avg rating) |
| `standings` | League table computed from results (3-1-0) |
| `competition_summary` | Champion, full table, relegated teams |
| `match_statistics` | Avg goals/match, home/away/draw rates |
| `biggest_wins` | Largest winning margins |
| `top_scoring_teams` | Teams ranked by goals scored |
| `best_venue_records` | Best home / away records |
| `list_competitions` | Competitions and seasons available |
| `dataset_info` | Loaded-data coverage report |

Every tool returns both a formatted text answer (for the LLM/user) and a
`structuredContent` JSON payload (for programmatic use).

---

## Usage

```bash
npm install      # install dependencies
npm run build    # compile TypeScript -> dist/
npm test         # run the BDD test suite (82 tests)
npm start        # run the MCP server over stdio
```

### Connecting to an MCP client (e.g. Claude Desktop)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

During development you can run directly from TypeScript with `npm run dev`.
The data directory can be overridden with the `BRAZILIAN_SOCCER_DATA_DIR`
environment variable (defaults to the bundled `data/kaggle`).

---

## Example questions it can answer

- "Show me all Flamengo vs Fluminense matches" → `search_matches`
- "Who won the 2019 Brasileirão?" → `competition_summary` (Flamengo, 90 pts)
- "What is Corinthians' home record in 2022?" → `team_record`
- "Find all Brazilian players" / "top Brazilian players" → `search_players`
- "Compare Palmeiras and Santos head-to-head" → `head_to_head`
- "What's the average goals per match in the Brasileirão?" → `match_statistics`
- "Show me the biggest wins in the dataset" → `biggest_wins`

See `tests/sample-questions.test.ts` for 24 worked examples.

### Note on the FIFA player data

The bundled FIFA dataset is the *FIFA 19* global player database. It contains
some Brazilian-league clubs (Grêmio, Cruzeiro, Internacional, Fluminense,
Santos, Atlético Mineiro, Botafogo, Bahia) but **not** every club (e.g. no
Flamengo/Palmeiras squad), and players are listed under their 2019 clubs
(e.g. Neymar Jr at PSG, Gabriel Jesus at Manchester City). Player queries
reflect that source faithfully.

---

## Testing

BDD scenarios live in `features/*.feature`; their executable counterparts are in
`tests/*.test.ts` (Given/When/Then structure):

- `normalize.test.ts` — name/date/number normalization edge cases
- `data.test.ts` — all 6 files load; overlap dedup is correct
- `matches.test.ts`, `teams.test.ts`, `players.test.ts`,
  `competitions.test.ts` — one file per capability category
- `server.test.ts` — drives the real MCP server through an in-memory transport
- `sample-questions.test.ts` — 24 spec sample questions

Performance (local): full data load ~330 ms (once, cached); simple lookups and
aggregate queries 2–5 ms — comfortably within the spec's < 2 s / < 5 s targets.

---

## Data Sources

Kaggle data requires an account to download, so these freely-available
(attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0
  - `fifa_data.csv`

## Specification

See `brazilian-soccer-mcp-guide.md` (and `TASK.md`) for the full requirements.
