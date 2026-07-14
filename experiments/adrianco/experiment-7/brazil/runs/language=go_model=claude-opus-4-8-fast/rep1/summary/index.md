# Architecture Summary

`brazilian-soccer-mcp` — a dependency-free (stdlib-only) Go MCP server answering
Brazilian-soccer questions over a stdio JSON-RPC 2.0 transport.

## Modules

| Package | Files | Responsibility |
|---------|-------|----------------|
| `main` | `main.go` | Entrypoint: load datasets (`-data`/`SOCCER_DATA_DIR`), register tools, serve on stdin/stdout. Logs to stderr to keep the JSON-RPC stream clean. |
| `internal/mcp` | `mcp.go` | Minimal MCP server: JSON-RPC 2.0 read/dispatch/write loop; `initialize`, `ping`, `tools/list`, `tools/call`; `AddTool` registry. |
| `internal/store` | `model.go`, `load.go`, `query.go`, `normalize.go` | Data model (`Match`, `Player`, `TeamRecord`), CSV loaders (one parser per dataset), query/aggregation helpers, and team-name normalization (accent-folding + state/country suffix stripping + dedup keys). |
| `internal/server` | `server.go` | Wires the store to 8 MCP tools: defines JSON schemas, decodes args, formats plain-text answers. |

## Data flow

1. `store.Load(dir)` reads the six Kaggle CSVs (5 match files + `fifa_data.csv`),
   normalizes competition labels (`canonComp`), drops overlapping BR-Football
   rows for authoritative competitions, and de-duplicates fixtures (`dedupKey`).
2. Tools call store query helpers (`FindMatches`, `HeadToHead`, `TeamStats`,
   `Standings`, `CompetitionStats`, `BiggestWins`, `SearchPlayers`) over the
   in-memory slices.
3. Team filters route through `TeamMatches`/`TeamKey` so a plain query
   ("Flamengo") matches every dataset spelling ("Palmeiras-SP", "São Paulo").

## Tools exposed

`find_matches`, `head_to_head`, `team_stats`, `standings`, `search_players`,
`competition_stats`, `biggest_wins`, `list_competitions`.

## Tests

35 `Test*` functions across `mcp`, `store`, and `server` packages
(`mcp_test.go`, `store_test.go`, `normalize_test.go`, `server_test.go`),
0 skipped. Coverage 0.843 (from `scores.json`).
