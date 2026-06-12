# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that answers natural-language
questions about Brazilian soccer — matches, teams, players, competitions and
statistics — over the bundled Kaggle datasets. Built in TypeScript with a
test-driven workflow (88 unit/integration tests).

It implements the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What it does

The server loads six CSV datasets into an in-memory query engine and exposes
eight MCP tools. An LLM (or any MCP client) can call these tools to answer the
sample questions in the spec, e.g. *"Show me all Flamengo vs Fluminense
matches"*, *"What is Corinthians' home record in 2022?"*, *"Who won the 2019
Brasileirão?"*, *"Find the highest-rated Brazilian players"*.

### MCP tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Find matches by team, opponent, competition, season or date range. Appends a head-to-head summary when two teams are given. |
| `team_record` | A team's W/D/L record, goals and points — filterable by season, competition and home/away venue. |
| `head_to_head` | Two teams compared: meetings, wins each, draws, and the match list. |
| `standings` | Final points table for a competition + season, computed from match results. |
| `match_statistics` | Average goals, home/away win rates and draw rate over a filtered set of matches. |
| `biggest_wins` | Matches with the largest goal margins. |
| `search_players` | FIFA player search by name, nationality, club or position, sorted by rating. |
| `brazilian_players_by_club` | Brazilian players grouped by their (Brazilian) club, with counts and average rating. |

## Datasets

Loaded from `data/kaggle/` (see attributions below). Raw row counts:

| File | Competition / content | Rows |
|------|-----------------------|-----:|
| `Brasileirao_Matches.csv` | Brasileirão Série A (2012–2023) | 4,180 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil | 1,337 |
| `Libertadores_Matches.csv` | Copa Libertadores | 1,255 |
| `BR-Football-Dataset.csv` | Série A/B/C + Copa do Brasil with extended stats | 10,296 |
| `novo_campeonato_brasileiro.csv` | Historical Brasileirão (2003–2019) | 6,886 |
| `fifa_data.csv` | FIFA player database | 18,207 |

## Design notes

The datasets overlap heavily (Brasileirão Série A 2019, for example, appears in
three files) and use inconsistent team-name spellings, so naïvely concatenating
them double- or triple-counts fixtures. Two normalization steps handle this:

- **Team-name normalization** (`src/normalize.ts`): strips accents, lower-cases
  and removes state suffixes (`Palmeiras-SP` → `palmeiras`) and country codes
  (`Nacional (URU)` → `nacional`). Clubs that share a base name are
  disambiguated by their state so they don't collapse together
  (`Atletico-MG` → `atletico mineiro`, `Atletico-PR` → `athletico paranaense`).
  Multiple date formats (ISO, `DD/MM/YYYY`, with/without time) are parsed.

- **Canonicalization** (`canonicalMatches`): for each `(competition, season)`,
  only the single most complete source file is kept. Because naming is
  self-consistent within one file, derived standings and statistics are correct
  (e.g. Flamengo's 2019 Série A title computes to exactly 90 points).

## Architecture

```
src/
  normalize.ts  Accent/suffix normalization, team matching, date parsing
  loader.ts     Per-dataset CSV parsers + canonicalization
  database.ts   SoccerDatabase: matches, records, standings, stats, players
  format.ts     Human-readable answer formatting
  tools.ts      MCP tool registry (Zod-validated) bound to the database
  server.ts     MCP server wiring (buildServer / runStdio)
  index.ts      Entry point: load data, serve over stdio
```

Each layer is unit-tested in isolation (`tests/`), with an integration test that
exercises the real CSV files and a server test that drives the MCP layer through
an in-memory client.

## Usage

```bash
npm install
npm test          # run the test suite (vitest)
npm run build     # compile TypeScript to dist/
npm start         # run the MCP server over stdio
```

The data directory defaults to `data/kaggle` next to the package; override it
with `BRAZILIAN_SOCCER_DATA_DIR`.

### Connecting an MCP client

Add to your MCP client configuration (e.g. Claude Desktop's
`claude_desktop_config.json`), after `npm run build`:

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

During development you can run the TypeScript directly with `npm run dev`
(uses `tsx`).

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets were downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank — Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`

## Specification

`brazilian-soccer-mcp-guide.md`
