# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
TypeScript, that exposes a natural-language-friendly query interface over
Brazilian soccer datasets (matches, teams, players, competitions, and aggregate
statistics). Implemented from the specification in
[`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md) (also mirrored
in [`TASK.md`](./TASK.md)).

## What it does

On startup the server loads all six provided CSV files into memory, normalizes
them into a single match model plus a player model, and serves eleven MCP tools.
An MCP-capable LLM client calls these tools to answer questions such as *"Who won
the 2019 Brasileirão?"*, *"Compare Palmeiras and Santos head-to-head"*, or *"Who
are the top Brazilian players?"*.

### MCP tools

| Category | Tool | Answers questions like |
|----------|------|------------------------|
| Match | `find_matches` | "What matches did Palmeiras play in 2023?", "Find Copa do Brasil matches" |
| Match | `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| Match | `last_meeting` | "When did Flamengo last play Corinthians? What was the score?" |
| Team | `team_record` | "What is Corinthians' home record in 2021?" |
| Player | `search_players` | "Who is Neymar?", "Highest-rated players at Flamengo", "Forwards from São Paulo" |
| Player | `players_by_club_summary` | "Brazilian players at Brazilian clubs" |
| Competition | `league_standings` | "Show the 2019 Brasileirão final standings" |
| Competition | `competition_champion` | "Who won the 2019 Brasileirão?" |
| Stats | `aggregate_stats` | "What's the average goals per match in the Brasileirão?" |
| Stats | `biggest_wins` | "Show me the biggest wins in the dataset" |
| Stats | `top_scoring_teams` | "Which team scored the most goals in Serie A 2023?" |

## Architecture

```
src/
  types.ts               Domain types (Match, Player, standings rows, records)
  normalize.ts           Team-name / date / goal normalization across datasets
  csv.ts                 CSV loading (BOM + quoted fields + UTF-8)
  dataStore.ts           Loads all six CSVs into normalized in-memory collections
  format.ts              Human-readable formatting of results
  server.ts              MCP server: registers the eleven query tools
  index.ts               Entry point: load data, serve over stdio
  queries/
    filters.ts           Shared match-filtering primitives
    matches.ts           find / head-to-head / last-meeting
    teams.ts             win-draw-loss records, home/away splits
    competitions.ts      league-standings calculation + champions
    players.ts           player search / ranking / club summaries
    stats.ts             aggregates, biggest wins, top scorers
tests/                   BDD-style Vitest suites (unit + real-data + MCP e2e)
```

### Data-quality handling

The datasets disagree on naming, dates, and encodings; the spec calls these out
explicitly and the implementation handles each:

- **Team-name variations** — `"Palmeiras-SP"`, `"Palmeiras"`, `"América - MG"`,
  `"Nacional (URU)"` are normalized by stripping state/country suffixes and
  parentheticals, then compared accent- and case-insensitively (`normalize.ts`).
  For **standings**, a *suffix-preserving* identity key keeps genuinely distinct
  clubs apart (e.g. `Atlético-MG` vs `Atlético-PR`) so they are never merged.
- **Date formats** — ISO (`2012-05-19 18:30:00`), plain ISO (`2023-09-24`), and
  Brazilian `DD/MM/YYYY` (`29/03/2003`) are all parsed.
- **Goal formats** — integers, floats (`2.0`), blanks and `NA` are handled;
  matches without a score are excluded from calculations.
- **Encoding** — files are read as UTF-8 with BOM stripping (the FIFA export
  starts with a BOM).
- **Overlapping datasets** — Brasileirão Série A appears in both
  `novo_campeonato_brasileiro.csv` (2003–2019) and `Brasileirao_Matches.csv`
  (2012–2022). Standings pick a single source per season to avoid
  double-counting fixtures.

## Getting started

```bash
npm install
npm run build
npm test        # run the BDD test suite
npm start       # start the MCP server on stdio
```

The data directory defaults to `./data/kaggle` and can be overridden with the
`SOCCER_DATA_DIR` environment variable.

### Using it as an MCP server

Register the built server with any MCP client (e.g. Claude Desktop / Claude Code):

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

## Testing

Tests are written BDD-style (Given/When/Then, behaviour-named scenarios) with
[Vitest](https://vitest.dev) and cover: normalization edge cases, each query
module against both hand-built and the real datasets, and an end-to-end pass
through a real MCP client/server pair over an in-memory transport.

```bash
npm test
```

Sample verified results (calculated purely from the match data):

- 2019 Brasileirão champion: **Flamengo, 90 pts (28W 6D 4L)** — matches the spec.
- 2017 Brasileirão champion: **Corinthians, 72 pts**.
- 2003 Brasileirão (24 teams): **Cruzeiro, 100 pts**.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

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
