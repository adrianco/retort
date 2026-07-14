# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a queryable knowledge interface over Brazilian soccer data — matches,
teams, players, competitions and aggregate statistics — so an LLM can answer
natural-language questions about Brazilian football.

Built in **TypeScript** against the spec in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (also mirrored
in `TASK.md`).

---

## What was built

- A **data layer** that loads all six bundled Kaggle CSV files (UTF-8) and
  normalizes their heterogeneous schemas into two unified in-memory shapes —
  `Match` and `Player` — totalling **~24,000 matches** and **18,207 players**.
- A **normalization layer** (`src/data/normalize.ts`) that handles the data
  quality issues called out in the spec:
  - state suffixes (`Palmeiras-SP`), country suffixes (`Nacional (URU)`) and
    space-separated state codes (`Botafogo RJ`);
  - accent-insensitive matching (`São Paulo` ≡ `Sao Paulo`);
  - multiple date formats (ISO `2023-09-24`, Brazilian `29/03/2003`, and
    timestamps `2012-05-19 18:30:00`);
  - canonical aliases for clubs the datasets spell inconsistently across files
    (`Vasco` / `Vasco da Gama` / `Vasco Da Gama RJ`; `Atlético` vs `Athletico`).
- A **query layer** (`src/queries/`) covering the five capability categories in
  the spec, with deduplication so the overlapping source files don't
  double-count matches in standings and statistics.
- An **MCP server** (`src/server.ts`, `src/index.ts`) exposing **10 tools** over
  stdio.
- A **BDD test suite** (`tests/`, 42 scenarios) structured as Given/When/Then
  Gherkin-style scenarios, including known-answer checks (e.g. Flamengo won the
  2019 Brasileirão with 90 points).

Every source file begins with a `Context` comment block describing its purpose.

---

## MCP Tools

| Category | Tool | Description |
|----------|------|-------------|
| Match | `search_matches` | Search matches by team, opponent, competition, season and/or date range |
| Match | `head_to_head` | All-time head-to-head record between two teams |
| Team | `team_stats` | W/D/L record, goals and win rate (overall / home / away) |
| Player | `search_players` | Search FIFA players by name, nationality, club, position, min rating |
| Player | `club_squad` | Squad list for a club, ranked by overall rating |
| Competition | `standings` | League table for a competition + season, computed from results |
| Competition | `season_summary` | Champion and relegation zone for a season |
| Stats | `aggregate_stats` | Avg goals/match, home/away win rates for a slice |
| Stats | `biggest_wins` | Matches with the largest goal margins |
| Stats | `top_scoring_teams` | Teams ranked by goals scored |

Competitions recognised: `Brasileirão Série A`, `Brasileirão Série B`,
`Brasileirão Série C`, `Copa do Brasil`, `Copa Libertadores`.

---

## Getting started

```bash
npm install      # install dependencies
npm run build    # compile TypeScript to dist/
npm test         # run the BDD test suite (42 scenarios)
npm start        # run the MCP server over stdio
```

For local development without a build step:

```bash
npm run dev      # run src/index.ts directly via tsx
```

### Connecting to an MCP client

Add the server to your client config (e.g. Claude Desktop's
`claude_desktop_config.json`), pointing at the built entrypoint:

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

The server loads the bundled `data/kaggle/` CSVs at startup (diagnostics are
written to stderr so the stdio JSON-RPC stream stays clean).

---

## Sample questions it can answer

These map onto the tools above (well beyond the 20-question success criterion):

1. *Show me all Flamengo vs Fluminense matches* → `search_matches`
2. *What matches did Palmeiras play in 2019?* → `search_matches`
3. *Find all Copa Libertadores matches* → `search_matches`
4. *When did Flamengo last play Corinthians?* → `search_matches`
5. *Compare Palmeiras and Santos head-to-head* → `head_to_head`
6. *What is Corinthians' home record in 2022?* → `team_stats`
7. *How did Flamengo perform in the 2019 Brasileirão?* → `team_stats`
8. *Find all Brazilian players in the dataset* → `search_players`
9. *Who are the highest-rated Brazilian players?* → `search_players`
10. *Show me all goalkeepers from Brazil* → `search_players`
11. *Who is Neymar?* → `search_players`
12. *Which players play for Santos?* → `club_squad`
13. *Who won the 2019 Brasileirão?* → `standings` / `season_summary`
14. *Show the final 2018 Brasileirão table* → `standings`
15. *Which teams were relegated in 2019?* → `season_summary`
16. *What's the average goals per match in the Brasileirão?* → `aggregate_stats`
17. *What is the home win rate in Série A?* → `aggregate_stats`
18. *Show me the biggest wins in the Brasileirão* → `biggest_wins`
19. *Which team scored the most goals in 2019?* → `top_scoring_teams`
20. *Compare the 2018 and 2019 seasons* → `aggregate_stats` (per season)

---

## Project layout

```
src/
  data/
    types.ts        unified Match / Player / Dataset types
    normalize.ts    team-name & date normalization, aliases
    loader.ts       per-file CSV parsers → unified dataset (cached)
  queries/
    common.ts       filtering, dedup, outcome & formatting helpers
    matches.ts      search_matches, head_to_head
    teams.ts        team_stats
    players.ts      search_players, club_squad
    competitions.ts standings, season_summary
    stats.ts        aggregate_stats, biggest_wins, top_scoring_teams
  server.ts         MCP server: registers and wires all tools
  index.ts          stdio entrypoint
tests/              BDD (Given/When/Then) specs, one per feature
data/kaggle/        bundled source CSVs
```

---

## Testing approach

Tests use **Vitest** with BDD-style `Feature` / `Scenario` structure mirroring
the Gherkin in the spec. Coverage spans normalization, data loading, and every
query category, plus an end-to-end MCP integration test that drives the wired
server through a real MCP client over an in-memory transport. Notable
known-answer assertions:

- 2019 Brasileirão → 20 teams, every team plays 38 games, **Flamengo champions
  on 90 points** (validates cross-source deduplication and name normalization).
- Head-to-head totals are symmetric and partition into wins/draws/losses.
- Win/draw rates sum to 100%; standings points equal `3·W + D`.

```bash
npm test
# Test Files  8 passed (8)
#      Tests  42 passed (42)
```

---

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

> **Note on the FIFA dataset:** this edition includes many but not all Brazilian
> clubs (e.g. Santos, Grêmio, Internacional, Cruzeiro and Atlético Mineiro are
> present; some others such as Flamengo are not), which is expected for player
> queries.

---

## License

MIT (server code). Bundled datasets retain their original licenses listed above;
intended for demo / non-commercial use.
