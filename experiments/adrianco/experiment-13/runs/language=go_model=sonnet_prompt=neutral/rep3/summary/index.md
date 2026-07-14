# Architecture Summary — brazilian-soccer-mcp (go, sonnet, neutral, rep3)

A single-package (`package main`) Go MCP server, stdlib-only (no external deps), exposing
Brazilian soccer queries over JSON-RPC 2.0 on stdio.

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Entrypoint: locates `data/kaggle/`, calls `LoadAll`, starts the stdio server. |
| `mcp_server.go` | Hand-rolled MCP JSON-RPC 2.0 layer: `initialize`, `ping`, `tools/list`, `tools/call`; request/response framing. |
| `tools.go` | Tool registry (`allTools`) + dispatch (`dispatchTool`) for 7 tools; arg coercion helpers; result formatting. |
| `query.go` | Query engine over in-memory data: match filtering, head-to-head, team stats, standings, biggest wins, competition stats, player search; formatters. |
| `loader.go` | CSV ingestion for all 6 datasets, date/number normalization, primary-source flagging, and de-duplication across overlapping datasets. |
| `normalize.go` | Team-name normalization (diacritics, state suffixes) and fuzzy `teamMatches`. |
| `models.go` | `Match`, `Player`, `TeamStats` structs + derived metrics (`GoalDiff`, `WinRate`). |
| `server_test.go` | 22 test functions covering loading, normalization, each query tool, the MCP protocol, and sample questions. |

## Data flow

`main` → `LoadAll(dataDir)` parses 6 CSVs into `Database{Matches, Players}` (deduped, primary-flagged) →
`Server.Run` reads JSON-RPC lines → `dispatchTool` routes to a `query.go` function → formatted text
returned as MCP `content`.

## Tools exposed

`search_matches`, `get_team_stats`, `head_to_head`, `search_players`, `get_standings`,
`get_biggest_wins`, `get_competition_stats`.

## Notes

- De-duplication logic (`loader.go`) carefully avoids double-counting Serie A matches that appear in
  multiple datasets via the `IsPrimary` flag and a `(date|home|away)` key.
- Extended match stats (corners, shots, attacks) are parsed and merged but not surfaced by any tool.
