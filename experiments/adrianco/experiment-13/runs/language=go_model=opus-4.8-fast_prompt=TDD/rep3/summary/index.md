# Architecture Summary — Brazilian Soccer MCP Server (Go)

> Generated inline by `evaluate-run` (the `run-summary` skill was not invocable in this environment).

## Modules

| Package | Files | Role |
|---------|-------|------|
| `cmd/server` | `main.go` | Entry point: loads `data/kaggle` CSVs into an in-memory DB, runs the MCP server over stdio. |
| `internal/soccer` | `model.go`, `loader.go`, `query.go`, `normalize.go`, `canonical.go`, `dedup.go` | Domain core: data model, per-file CSV parsers, the query engine, and team-name normalization/deduplication. |
| `internal/mcpserver` | `server.go`, `tools.go`, `format.go` | MCP/JSON-RPC 2.0 stdio transport, tool definitions, dispatch to the query engine, and human-readable answer formatting. |

## Data flow

1. `main` calls `soccer.Load(dir)` → one parser per CSV layout (`parseBrasileirao`, `parseCup`, `parseLibertadores`, `parseBRFootball`, `parseNovo`, `parsePlayers`) maps each file's columns/date-format/naming into the common `Match`/`Player` model.
2. Matches are deduplicated across overlapping source files (`dedupeMatches`); team names are canonicalized (accent/suffix-insensitive).
3. `mcpserver.NewServer(NewHandler(db))` exposes six tools; `Serve` reads newline-delimited JSON-RPC requests and dispatches `initialize` / `tools/list` / `tools/call` (+ `ping`, notifications).
4. Each `tools/call` is coerced (`argString`/`argInt`) and routed to a query-engine method, then formatted to text.

## MCP tools (interfaces)

`search_matches`, `head_to_head`, `team_record`, `standings`, `search_players`, `match_statistics` — covering match/team/player/competition/statistical query categories.

## Query engine (internal/soccer/query.go)

`FindMatches`, `HeadToHead`, `TeamRecord`, `Standings`, `FindPlayers`, `AverageGoals`, `HomeWinRate`, `BiggestWins`. Filtering is centralized in `Match.matches(MatchFilter)`; team matching is accent/suffix-insensitive via `TeamMatches`/`removeAccents`.

## Notable design choices

- Resilient CSV reading: `FieldsPerRecord=-1`, `LazyQuotes`, BOM-stripped header-name → index map (avoids the missing-key→index-0 trap).
- Tool errors surfaced as MCP `result.isError`, not protocol errors (per MCP spec).
- Diagnostics go to stderr to keep the stdout JSON-RPC stream clean.
