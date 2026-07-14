# Brazilian Soccer MCP Server (Clojure)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a
knowledge graph of Brazilian soccer data as callable tools, so an LLM can answer
natural-language questions about players, teams, matches and competitions.

The full specification this implements is in **`brazilian-soccer-mcp-guide.md`**
(also mirrored in `TASK.md`).

## What was built

* An **in-memory knowledge graph** built at startup from the six provided Kaggle
  CSV files — no external database or network service is required.
* An **MCP stdio server** speaking newline-delimited JSON-RPC 2.0
  (`initialize`, `tools/list`, `tools/call`, `ping`, notifications).
* **Nine tools** covering all five capability groups from the spec:

  | Tool | Capability |
  |------|------------|
  | `find_matches` | Match queries by team / opponent / competition / season / date range |
  | `head_to_head` | Rivalry record (wins, draws, goals, recent meetings) |
  | `team_stats` | Win/draw/loss record, goals, win rate (filterable by season/competition/home/away) |
  | `find_players` | FIFA player search by name / nationality / club / position / min rating |
  | `standings` | League table computed from match results |
  | `league_stats` | Average goals per match, home/away win rates, draw rate |
  | `biggest_wins` | Largest-margin matches |
  | `list_competitions` | Competitions, season coverage, counts |
  | `graph_info` | Diagnostics (matches/players/teams/competitions loaded) |

Loaded graph size: **20,179 matches**, **18,207 players**, **497 teams**,
**5 competitions** (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores).

## Data normalisation

The datasets disagree on how they spell the same entity, so a single
normalisation layer (`src/brazilian_soccer/normalize.clj`) reconciles them:

* **Team names** – state/country suffixes are dropped (`Palmeiras-SP` → `Palmeiras`,
  `Nacional (URU)` → `Nacional`) *except* where the state is part of a club's
  identity (`Atlético-MG` vs `Atlético-PR`, `América-MG`).
* **Accents/cedilla** – stripped for matching keys (`São Paulo` ↔ `Sao Paulo`).
* **Dates** – the three formats (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`)
  are all parsed to ISO `yyyy-MM-dd`.
* **Cross-source de-duplication** – the same real fixture appearing in several
  files is merged on `[competition, home, away, date]`, keeping the richest
  record and unioning the source set; league standings additionally use a single
  primary source per season to avoid double counting.

## Architecture

```
src/brazilian_soccer/
  normalize.clj        normalisation rules (names, accents, dates, numbers)
  data_loader.clj      reads the 6 CSVs into uniform match/player records
  knowledge_graph.clj  builds & caches the graph (nodes + indexes, dedup)
  queries.clj          pure analytics (matches, stats, standings, players)
  format.clj           renders query data as the spec's answer formats
  mcp_server.clj       JSON-RPC 2.0 stdio MCP server (main entry point)
```

## Running

Requires the Clojure CLI and a JDK.

Start the MCP server (reads JSON-RPC on stdin, writes on stdout; diagnostics on
stderr):

```bash
clojure -M -m brazilian-soccer.mcp-server
```

### Example MCP client config

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M", "-m", "brazilian-soccer.mcp-server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Quick manual smoke test

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}' \
 | clojure -M -m brazilian-soccer.mcp-server
```

## Testing

BDD-style (Given/When/Then) `clojure.test` suites cover normalisation, loading,
graph construction/dedup, every query, and the MCP JSON-RPC layer (including a
full stdio round-trip):

```bash
clojure -M:test
```

→ `Ran 34 tests containing 112 assertions. 0 failures, 0 errors.`

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
