# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server, written
in Go, that answers natural-language questions about Brazilian soccer — matches,
teams, players, competitions and statistics — over the bundled Kaggle datasets.
An LLM client connects to the server, discovers its tools, and calls them to
retrieve match results, team records, head-to-head comparisons, FIFA player
data, calculated league standings and aggregate statistics.

The full requirements are in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in `TASK.md`).

## What was built

A self-contained MCP server (Go standard library only — **no external
dependencies**) that:

- Loads all **six** provided CSV datasets (4 match files + 1 historical match
  file + 1 FIFA player file) into an in-memory store at start-up.
- Speaks the MCP stdio transport: newline-delimited JSON-RPC 2.0, with the
  `initialize` handshake, `tools/list` discovery, and `tools/call` execution.
- Exposes **six tools** covering every required query category.
- Normalizes the datasets' messy real-world data: team-name state suffixes
  (`Palmeiras-SP`, `Nacional (URU)`), Portuguese accents (`São Paulo`, `Grêmio`),
  multiple date formats (`2019-05-01`, `29/03/2003`, `2012-05-19 18:30:00`),
  float-encoded scores (`2.0`) and UTF-8 throughout.

### Tools

| Tool | Category | What it answers |
|------|----------|-----------------|
| `find_matches` | Match queries | Matches by team, opponent, competition, season and/or date range. With both a team and opponent, also returns the head-to-head summary. |
| `team_record` | Team queries | A team's W/D/L record, goals for/against and win rate, optionally by season, competition and venue (home/away). |
| `head_to_head` | Statistical analysis | Two teams compared: meetings, wins each, draws, goals, and the match list. |
| `search_players` | Player queries | FIFA players by name, nationality, club and/or position, sorted by overall rating. |
| `competition_standings` | Competition queries | A calculated league table for a competition + season (3 pts win / 1 draw), sorted by points then goal difference. |
| `match_statistics` | Statistical analysis | Average goals per match, home/away/draw rates, and the biggest victories. |

### Example (calculated 2019 Brasileirão standings)

```
Brasileirão 2019 Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) GF:86 GA:37 GD:+49
2. Palmeiras - 74 pts (21W, 11D, 6L) GF:61 GA:32 GD:+29
3. Santos - 74 pts (22W, 8D, 8L) GF:60 GA:33 GD:+27
...
```

(Flamengo's 90 pts / 28-6-4 matches the real 2019 result.)

## Build, test and run

Requires Go 1.23+.

```sh
# Run the executable acceptance + unit test suite
go test ./...

# Build the server
go build -o brazilian-soccer-mcp .

# Run it (reads JSON-RPC from stdin, writes to stdout; logs to stderr)
./brazilian-soccer-mcp
```

The data directory defaults to `data/kaggle`. Override with the `-data` flag or
the `BRAZIL_SOCCER_DATA_DIR` environment variable.

### Connecting from an MCP client

Configure the client to launch the binary as a stdio MCP server, e.g.:

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

### Quick manual check

```sh
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Palmeiras","team_b":"Santos"}}}' \
 | ./brazilian-soccer-mcp
```

## How it was built — ATDD

This server was built with executable **Acceptance Test-Driven Development** in a
continuous-delivery style. Every requirement in the spec was first translated
into an automated acceptance test that drives the system **only through the MCP
protocol** (no back-door access to internals), asserting on *what* the system
does in the language of the domain ("find matches between two teams", "a team's
home record", "the league champion"). Those tests were written to fail first,
then the implementation was driven until they passed, with finer-grained unit
tests underneath for the data-cleaning internals.

- `mcpclient_test.go` — an in-process MCP client (initialize / list / call) used
  by every acceptance test, so the suite is genuinely black-box.
- `acceptance_test.go` — the executable specification. Most scenarios boot a
  fresh server over a tiny, self-contained fixture dataset (atomic and
  independent); a final group runs against the real bundled datasets to prove
  all six files load and that known facts hold (2019 champion Flamengo, top
  Brazilian player Neymar, all competitions queryable).
- `internals_test.go` — unit tests for name normalization, competition
  resolution and score/date parsing.

## Design notes

- **Team identity.** A team is keyed by its base name *plus* its state/country
  code, so `Atlético-MG`, `Atlético-PR` and `Atlético-GO` stay distinct, while a
  suffix-less query like "Flamengo" still matches "Flamengo-RJ".
- **Overlapping sources.** The datasets overlap heavily (the 2012–2019
  Brasileirão appears in three files) and disagree on spellings. To keep
  standings correct, each *(competition, season)* is sourced from a single
  authoritative file; lower-priority files fill in competition-seasons the
  authoritative ones lack (Série B/C and recent seasons).
- **No external dependencies.** Everything — CSV parsing, JSON-RPC framing,
  accent folding — uses the Go standard library, so the build is reproducible
  offline.
- Every source file begins with a context block comment describing its role.

## Source layout

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point: load data, run the stdio server. |
| `server.go` | MCP JSON-RPC 2.0 transport (initialize / tools/list / tools/call). |
| `tools.go` | The six tool definitions, schemas, argument handling and dispatch. |
| `store.go` | CSV loading, canonicalization, and all domain queries. |
| `model.go` | `Match` / `Player` domain types and team identity. |
| `names.go` | Team-name normalization and competition resolution. |
| `format.go` | Rendering query results as domain-language text. |

## Data & licenses

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md). Datasets are
bundled under `data/kaggle/` (CC BY 4.0 / CC0 / Apache 2.0 as noted there).
Demo / non-commercial use.
