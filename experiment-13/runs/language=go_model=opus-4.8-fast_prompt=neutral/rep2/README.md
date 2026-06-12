# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written in Go,
that answers natural-language questions about Brazilian soccer over the Kaggle datasets in
`data/kaggle/`. It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) / [`TASK.md`](TASK.md).

An MCP-capable LLM client (Claude Desktop, etc.) connects to the server over stdio,
discovers the tools, and calls them to answer questions about matches, teams, players,
competitions, and statistics.

## What it does

On startup the server loads all six CSV datasets into an in-memory knowledge base and
exposes eight tools over JSON-RPC 2.0. It needs no database, no network, and no
third-party Go dependencies — only the standard library.

### Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `search_players` | "Find all Brazilian players", "Highest-rated players at a club", "Forwards from a club" |
| `players_by_club` | "How many Brazilian players does each club have, and their average rating?" |
| `competition_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated?" |
| `match_statistics` | "Average goals per match", "Biggest wins", "Home vs away split" |
| `list_competitions` | "Which competitions and how much data are available?" |

Each tool publishes a JSON Schema for its arguments (visible via `tools/list`), so an LLM
can discover how to call it.

### Example output

`competition_standings(competition="Brasileirão", season=2019)`:

```
Brasileirão 2019 standings (computed from matches):
 1. Flamengo - 90 pts (28W 6D 4L, GD +49)
 2. Palmeiras - 74 pts (21W 11D 6L, GD +29)
 3. Santos - 74 pts (22W 8D 8L, GD +27)
 ...
```

(Matches the historical result — Flamengo were 2019 champions with 90 points.)

## Building and running

Requires Go 1.21+.

```bash
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp              # reads ./data/kaggle by default
./brazilian-soccer-mcp -data /path/to/kaggle
```

The data directory can also be set with the `BR_SOCCER_DATA` environment variable.
Diagnostics are written to **stderr**; the JSON-RPC protocol uses **stdout**, so the two
never mix.

### Quick manual check

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}' \
  | ./brazilian-soccer-mcp
```

### Using it from an MCP client

Example Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Testing

```bash
go test ./...
```

Tests cover three layers:

- **`internal/soccer`** — normalization, CSV loading, cross-dataset de-duplication, and
  every query function, using small hand-computed fixtures in
  `internal/soccer/testdata/kaggle`.
- **`internal/mcp`** — the JSON-RPC/MCP transport (initialize, tools/list, tools/call,
  notifications, error handling) over in-memory pipes.
- **`internal/server`** — the tool catalog and answer formatting.
- **`integration_test.go`** — validates results against the *real* datasets (e.g. the 2019
  Brasileirão champion and points total). Skips automatically if the data is absent.

## How it works

```
main.go                 entry point: resolve data dir, load, serve over stdio
internal/soccer/        domain model + CSV loaders + query/aggregation engine
internal/mcp/           minimal MCP server (JSON-RPC 2.0 over stdio)
internal/server/        wires soccer queries to MCP tools + formats answers
```

### Data quality handling

The datasets are messy in the ways the spec calls out, and the implementation addresses
each:

- **Team-name variations** — "Palmeiras-SP" vs "Palmeiras", "São Paulo" vs "Sao Paulo".
  Names are normalized to a cleaned display form plus an accent-folded, lowercase match
  key. A suffix-less query like "Flamengo" resolves to the canonical "Flamengo-RJ" via an
  alias map learned from the data, while genuinely distinct clubs that share a bare name
  (Atlético-MG vs Atlético-GO vs Athletico-PR) are kept separate by their state code.
- **Multiple date formats** — ISO, `DD/MM/YYYY`, and datetime forms are all parsed.
- **UTF-8 / accents and BOM** — handled throughout; a leading byte-order mark in the FIFA
  header is stripped.
- **Overlapping datasets** — the same Brasileirão season appears in three files with
  inconsistent naming, which would otherwise double- or triple-count results. For each
  `(competition, season)` the loader keeps a single authoritative source (the dedicated
  competition file over the broad multi-tournament file), so standings and records are
  counted exactly once. Seasons/competitions that exist in only one file (e.g. Série B/C)
  are preserved.

Every source file begins with a context comment block describing its role, per the
repository convention.

## Data sources & licenses

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md). The datasets under
`data/kaggle/` are used under their respective licenses (CC BY 4.0, CC0, Apache 2.0) for
this non-commercial demo.
