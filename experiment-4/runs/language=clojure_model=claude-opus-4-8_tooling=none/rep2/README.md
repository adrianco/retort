# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge
interface over six Brazilian-soccer datasets, so an LLM can answer natural
language questions about matches, teams, players, competitions and statistics.

Implemented in Clojure (tools.deps), speaking JSON-RPC 2.0 over stdio. See
[`TASK.md`](TASK.md) for the original specification.

## Quick start

```bash
# Run the MCP server (stdio JSON-RPC) — used by an MCP client / LLM
clojure -M:server

# Answer 20+ sample questions through the tools (great as a smoke test)
clojure -M:demo

# Run the BDD test suite
clojure -M:test
```

Requires a JDK and the Clojure CLI. Datasets live in `data/kaggle/` (override
the directory with the `BSOCCER_DATA_DIR` environment variable).

## What was built

```
src/brazilian_soccer/
  normalize.clj   Team-name canonicalisation (accents, suffixes, aliases)
  data.clj        Loads & unifies the 6 CSVs; de-duplicates overlapping data
  queries.clj     Pure query/analytics functions (the 5 spec categories)
  format.clj      Renders results into the spec's human-readable answer blocks
  mcp.clj         MCP tool catalogue + JSON-RPC request handler
  main.clj        stdio transport / entry point
  demo.clj        Runnable demonstration of 20+ sample questions
test/brazilian_soccer/
  normalize_test.clj  data_test.clj  queries_test.clj  mcp_test.clj
```

Each source file opens with a `Context` comment describing its role.

### Data handling

All six CSVs are loaded as UTF-8 into one unified, in-memory match schema plus a
player table. Three deliberate data-quality measures address the issues called
out in the spec:

1. **Team-name normalisation** (`normalize.clj`). A canonical key collapses
   accent/suffix/corporate variants (`Grêmio-RS` = `Gremio`, `EC Bahia` =
   `Bahia`, `Vasco Da Gama RJ` = `Vasco`) while keeping genuinely distinct clubs
   apart — notably `Atlético` (Mineiro) vs `Athletico` (Paranaense) vs
   `Atlético Goianiense`, which an explicit alias table disambiguates.
2. **Multi-format date parsing**. `2012-05-19 18:30:00`, `2023-09-24` and
   `29/03/2003` all normalise to ISO `yyyy-MM-dd`.
3. **Cross-file de-duplication**. The Brasileirão appears in up to three files,
   sometimes with off-by-one dates (COVID-delayed seasons) and divergent
   spellings. For each `(competition, season)` slice the loader keeps a single
   authoritative source — the dedicated league/cup files (which carry a real
   `season` column) over the broad BR-Football aggregate. This makes standings
   and aggregates correct: e.g. the computed 2019 Série A table crowns Flamengo
   with **90 pts (28W, 6D, 4L)**, matching reality.

### MCP tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team, opponent, competition, season, date range |
| `team_record` | W/D/L + goals record, scoped by season/competition/venue |
| `head_to_head` | Aggregate record and match list between two teams |
| `standings` | League table computed from results (3pts win, 1 draw) |
| `league_stats` | Avg goals/match, home & away win rates, draws |
| `biggest_wins` | Matches ordered by goal margin |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `club_nationality_breakdown` | Players of a nationality grouped by club |
| `list_competitions` / `list_seasons` | Discover available data |

### Performance

Data is parsed once and cached. After load, simple lookups run in single-digit
milliseconds and aggregate queries (standings, all-time stats) in well under
100 ms — comfortably inside the spec's 2 s / 5 s targets.

## Connecting an MCP client

Example entry for an MCP client config (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:server"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

The server logs diagnostics to **stderr** and emits JSON-RPC only on **stdout**,
so the protocol stream is never corrupted.

## Testing

BDD (Given/When/Then) scenarios using `clojure.test`, organised by layer:
normalisation, data loading/de-duplication, the five query categories, and the
MCP/JSON-RPC protocol. The suite asserts against known facts (e.g. Flamengo's
2019 title run, the Fla-Flu head-to-head) — 32 tests / ~1500 assertions.

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
