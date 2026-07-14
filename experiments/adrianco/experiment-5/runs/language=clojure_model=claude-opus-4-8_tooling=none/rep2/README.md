# Brazilian Soccer MCP with spec and basic data sets

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
**Clojure**, that exposes the six provided Brazilian-soccer datasets as a set of
query tools an LLM can call to answer natural-language questions about players,
teams, matches, competitions and statistics.

## Specification
brazilian-soccer-mcp-guide.md (also mirrored in `TASK.md`)

## Quick start

Requirements: a JDK (21+) and the [Clojure CLI](https://clojure.org/guides/install_clojure).

```bash
# Run the MCP server (speaks JSON-RPC 2.0 over stdio)
clojure -M:run

# Run the test suite (BDD Given/When/Then, clojure.test)
clojure -M:test
```

On startup the server loads ~28,000 matches and ~18,000 players into memory
(about 1 second cold), so every subsequent tool call answers in milliseconds —
well inside the spec's 2s/5s targets.

### Connecting from an MCP client

Add the server to your client's MCP configuration, e.g. for Claude Desktop
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:run"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

The data directory defaults to `data/kaggle`; override with the
`BR_SOCCER_DATA_DIR` environment variable.

## Architecture

```
src/brazilian_soccer/
  data.clj      Load the 6 CSVs; normalise team names, dates, integers.
  queries.clj   Pure query/aggregation logic (match/team/player/competition/stats).
  format.clj    Render results as the human-readable prose blocks from the spec.
  mcp.clj       JSON-RPC 2.0 stdio server + MCP tool registry (entry point).
test/brazilian_soccer/
  fixtures.clj      Hand-verifiable sample data for exact assertions.
  data_test.clj     Normalisation / parsing / dataset-loading tests.
  queries_test.clj  Query-logic tests (fixtures + real-data smoke checks).
  mcp_test.clj      JSON-RPC handshake, tools/list, tools/call, stdio round-trip.
```

Every source file opens with a "CONTEXT" block comment describing its role.

## MCP tools

| Tool | Purpose | Spec category |
|------|---------|---------------|
| `search_matches` | Find matches by team, opponent, home/away, competition, season, date range | Match queries |
| `head_to_head` | Aggregated record + match list between two teams | Match / statistical |
| `team_stats` | W/D/L and goals for a team (by season, competition, home/away) | Team queries |
| `standings` | League table computed from results (3pts/win) | Competition queries |
| `competition_stats` | Match count, total/avg goals, home/away/draw rates | Statistical analysis |
| `biggest_wins` | Matches ranked by goal margin | Statistical analysis |
| `search_players` | FIFA players by name, nationality, club, position, min rating | Player queries |
| `top_players` | Highest-rated players, optionally filtered | Player queries |
| `list_competitions` | Discover competitions, seasons and dataset coverage | — |

Each tool returns both a formatted prose answer and the raw result as a JSON
block, so a client can present the prose directly or reason over the structure.

## Data-quality handling

The datasets use inconsistent conventions; the server normalises them:

- **Team names** — parentheticals (`Nacional (URU)`) are dropped, while the
  state/country suffix is *kept* (`Atlético-MG` vs `Atlético-PR`) because it
  disambiguates same-named clubs. Fuzzy, accent-insensitive matching still lets
  `"Flamengo"` match `"Flamengo-RJ"` and `"São Paulo"` match `"Sao Paulo"`.
- **Dates** — ISO (`2012-05-19 18:30:00`), bare ISO and Brazilian `DD/MM/YYYY`
  are all parsed to sortable `YYYY-MM-DD`.
- **Encoding** — files are read as UTF-8; accents are folded only for matching.
- **Overlapping datasets** — the 2003-2019 historical Brasileirão and the
  2012-2023 Brasileirão file overlap. `standings` computes from a single
  canonical source per season for an exact table (e.g. **2019 Brasileirão →
  Flamengo, 90 pts, 28W 6D 4L**, matching the published result); other queries
  de-duplicate fixtures by season + teams + score. A few rows that differ in
  spelling/score between files cannot be perfectly reconciled without a
  team-name alias table, so cross-source aggregate counts are approximate.

## Tests

`clojure -M:test` runs 19 BDD-structured tests (105 assertions) covering
normalisation, every query type against exact fixtures, real-dataset smoke
checks, performance, and the full JSON-RPC/MCP protocol layer.

---

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
