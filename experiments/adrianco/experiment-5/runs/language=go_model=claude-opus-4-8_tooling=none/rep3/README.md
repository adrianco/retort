# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server, written
in Go, that exposes a queryable knowledge layer over six bundled Kaggle datasets
of Brazilian soccer matches and FIFA players. It lets an MCP-capable LLM answer
natural-language questions about matches, teams, players, competitions and
aggregate statistics. Implemented against the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) / [`TASK.md`](TASK.md).

## Quick start

```bash
# Build
go build -o bsmcp .

# Sanity check: print a dataset summary (no MCP client needed)
./bsmcp -info

# Run as an MCP server over stdio (this is how an MCP client launches it)
./bsmcp
```

The server loads `./data/kaggle` by default. Override with `-data <dir>` or the
`BR_SOCCER_DATA` environment variable. Diagnostics go to stderr; stdout carries
only the JSON-RPC stream.

### Registering with an MCP client

Example client configuration (e.g. Claude Desktop `mcpServers` entry):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/bsmcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The server speaks MCP revision `2024-11-05` over the stdio transport
(newline-delimited JSON-RPC 2.0) and implements `initialize`, `tools/list`,
`tools/call` and `ping`.

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, season range, date range or venue (home/away). |
| `team_record` | Win/draw/loss record, goals for/against, points and win rate for a team, optionally by season / competition / venue. |
| `head_to_head` | Head-to-head record and meeting list between two teams. |
| `search_players` | Search the FIFA player database by name, nationality, club, position and/or minimum overall rating (sorted by rating). |
| `standings` | League table for a competition/season, computed directly from match results. |
| `competition_stats` | Aggregate stats: matches, total/average goals per match, home/away win and draw rates. |
| `biggest_wins` | Most lopsided results by goal margin. |
| `dataset_info` | Counts and competitions of the loaded data. |

Example questions these cover (from the spec): *"Show me all Flamengo vs
Fluminense matches"*, *"What is Corinthians' home record in 2022?"*, *"Who won the
2019 Brasileirão?"*, *"Find all Brazilian players"*, *"What's the average goals per
match in the Brasileirão?"*, *"Compare Palmeiras and Santos head-to-head"*.

## How it works

```
main.go                      CLI entry point; loads data, serves MCP over stdio
internal/soccer/             data layer (loading, normalization, query engine)
  model.go                   Match / Player domain types
  normalize.go               team-name normalization (accents, state suffixes, aliases)
  load.go                    CSV loaders, one per dataset, into a shared model
  store.go                   in-memory Store + canonicalization + query/result types
  query.go                   the query engine (matches, teams, players, standings, stats)
  format.go                  human-readable answer formatting
internal/mcpserver/          MCP protocol (JSON-RPC 2.0 over stdio), no dependencies
  protocol.go                JSON-RPC + MCP payload shapes
  server.go                  read/dispatch/write loop and lifecycle methods
  tools.go                   tool schemas and handlers wrapping the query engine
```

The implementation has **no third-party dependencies** — only the Go standard
library.

### Data-quality handling

The datasets are messy in the ways the spec calls out, and the loader normalizes
them:

- **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, `São Paulo`,
  `Sao Paulo`, `Nacional (URU)`, `América - MG` all resolve to a stable matching
  key (lowercase, accent-folded, state/country suffix and parenthetical notes
  stripped), with a small alias table for cases like *Atlético-MG* vs
  *Atlético Mineiro* and *Vasco da Gama* vs *Vasco*.
- **Date formats** — ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) are all parsed.
- **UTF-8 / BOM** — accents are preserved in display names; the FIFA file's
  leading byte-order mark is stripped.
- **Cross-source duplication** — the same Brasileirão fixture appears in three
  files (and Copa do Brasil in two). To avoid triple-counting goals, matches and
  points, the store keeps, for each `(competition, season)`, only the matches
  from the single highest-priority source that actually covers that season. This
  makes the computed 2019 Brasileirão table reproduce the real result exactly:
  **Flamengo champions on 90 pts (28W 6D 4L)**, 20 teams, 380 matches.

## Testing

Behaviour-driven (Given/When/Then) tests load the real bundled datasets and
double as integration coverage:

```bash
go test ./...
```

They cover match search, venue restriction, team records, head-to-head symmetry,
the known 2019 standings and aggregate stats, player search/sorting/filtering,
name normalization (variants unify, distinct clubs stay distinct), and the full
MCP JSON-RPC round-trip (handshake, tools/list, tool calls, error handling).

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — License: CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — License: CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — License: CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — License: Apache 2.0
  - `fifa_data.csv` (FIFA 19 snapshot; some players appear under abbreviated names)
