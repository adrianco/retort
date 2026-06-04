# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written
in **Clojure**, that answers natural-language questions about Brazilian soccer —
matches, teams, players, competitions and statistics — over the bundled Kaggle
datasets. It speaks JSON-RPC 2.0 over stdio and can be wired directly into any
MCP-capable LLM client (Claude Desktop, etc.).

See [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
for the full specification this implements.

## What was built

A self-contained, in-memory **knowledge graph** loaded from the six provided CSVs.
No external database (e.g. Neo4j) is required, so the server starts in a couple of
seconds and the whole test-suite runs anywhere `clojure` is installed.

| Namespace | Responsibility |
|-----------|----------------|
| `brazilian-soccer.normalize` | Team-name normalization — strips state suffixes (`-SP`), country codes (`(URU)`) and accents; provides an accent-/punctuation-insensitive match key. |
| `brazilian-soccer.data` | Loads & unifies the 5 match datasets + the FIFA player dataset; handles multiple date formats, float/quoted goal values, UTF-8/BOM, and de-duplicates the overlapping Brasileirão sources. |
| `brazilian-soccer.queries` | Pure query/analytics layer: match search, team stats, head-to-head, league standings, competition aggregates, biggest wins, player search. |
| `brazilian-soccer.format` | Renders query results as the readable text shown in the spec. |
| `brazilian-soccer.mcp` | MCP JSON-RPC 2.0 transport, tool catalogue (`tools/list`) and dispatch (`tools/call`). |
| `brazilian-soccer.main` | Entry point — loads the data and serves MCP over stdio. |

### MCP tools exposed

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `standings` | "Who won the 2019 Brasileirão?" (table calculated from results) |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Santos?" |
| `players_by_club` | "Brazilian players grouped by club with average rating" |

## Requirements

- [Clojure CLI](https://clojure.org/guides/install_clojure) (tools.deps) — tested with 1.12
- A JDK (tested with OpenJDK 26)

Dependencies (`org.clojure/data.csv`, `org.clojure/data.json`) are fetched
automatically by the Clojure CLI on first run.

## Run

```bash
clojure -M:run
```

The server logs a readiness line to **stderr** (so it never corrupts the JSON-RPC
stream on stdout) and then reads newline-delimited JSON-RPC requests from stdin.

Quick manual smoke test:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":5}}}' \
  | clojure -M:run
```

### Wiring into an MCP client (e.g. Claude Desktop)

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

## Test

BDD-style (Given/When/Then) tests using `clojure.test`, covering normalization,
every query function (against a precise synthetic fixture *and* the real CSVs),
and the MCP request handler:

```bash
clojure -X:test
```

> 27 tests, 74 assertions — normalization, match/team/player queries, standings,
> statistics and the full MCP handshake + tool-call path.

## Data-quality handling

The spec calls out several real issues in the data, all handled:

- **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, `São Paulo` all resolve
  via an accent-insensitive match key. League tables group on the *raw* name so
  distinct clubs that share a base name (`Atlético-MG` vs `Atlético-GO`) are not
  conflated.
- **Overlapping Brasileirão sources** — the top flight appears in three datasets
  with different naming conventions; standings/aggregates use a single
  authoritative source per season, yielding correct 38-round tables. (Verified:
  the 2019 table reproduces the spec's example — Flamengo 90 pts, 28W 6D 4L.)
- **Multiple date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all
  normalized to `YYYY-MM-DD`.
- **Goal encodings** — `"1.0"`, `"2"` and quoted values are parsed to integers.
- **UTF-8 / BOM** — files are read as UTF-8 and the BOM on `fifa_data.csv` is
  stripped.

> Note: the FIFA dataset (licensing-limited) does not include some big Brazilian
> clubs such as Flamengo/Palmeiras/Corinthians, but does include Santos, Grêmio,
> Internacional, etc. Player-by-club queries reflect exactly what is in the data.

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
