# Architecture Summary

> The `run-summary` skill is not registered as an invocable skill in this session; this
> summary was produced inline during evaluation.

## Modules

| Package | File | Responsibility |
|---------|------|----------------|
| `main` | `main.go` | Entrypoint. Builds the data dir path, constructs `data.Loader`, calls `LoadAll()`, wraps it in `server.MCPServer`, prints counts and a hard-coded set of example queries. |
| `data` | `data/loader.go` | CSV ingestion + domain model. Defines `Match`, `Player`, `TeamStatistics`, `CompetitionStandings`. Loads 5 match CSVs + FIFA players, normalizes team names, and exposes query helpers (by team, season, competition; player by name/club/position/nationality). |
| `server` | `server/server.go` | Query/aggregation layer over `data.Loader`. `MCPServer` struct with ~25 methods: match finders, team statistics, head-to-head, standings, average goals, home win rate, biggest wins, player search. |

## Data flow

`main.go` → `data.NewLoader(dataDir)` → `LoadAll()` reads
`data/kaggle/*.csv` into per-competition slices → `server.NewMCPServer(loader)` →
methods call back into the loader's `GetAllMatches()` / `GetPlayers()` and filter/aggregate
in memory. All queries are direct Go method calls; there is **no network/protocol layer**.

## Key gap

The type is named `MCPServer`, but there is no Model Context Protocol implementation:
no JSON-RPC/stdio transport, no tool registration or schemas, and `go.mod` declares zero
dependencies. It is a queryable in-memory library, not an MCP server — the defining
requirement (R1) is only partially met.

## Notable correctness point

`GetHeadToHead` (server.go:120) aggregates per-side goals correctly, but
`GetTeamStatistics` (server.go:89-90) does not — it always attributes home/away goals to
for/against regardless of which side the team played. See `findings.jsonl` R6.
