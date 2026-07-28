# Architecture summary — brazilian-soccer (go, hermes-local, m80) rep2

> The `run-summary` skill was not available in this session; this is a hand-written
> stand-in so the evaluation's link is not dead.

## Package layout

Single Go package `server` (module `brazilian-soccer-mcp`, `go 1.21`), three source
files + one test file. **No `package main` / entrypoint exists** — the code is a
library, not a runnable (MCP) server.

| File | LOC | Responsibility |
|------|-----|----------------|
| `server/data.go` | 1198 | Domain types (`Match`, `Player`, `TeamStats`, `CompetitionTable`), CSV loaders for all 6 datasets, `DataStore` query methods, team-name normalization. `DataDir` resolved at runtime in `init()`. |
| `server/query.go` | 715 | `QueryEngine` — natural-language `Query(string)` dispatcher that keyword-routes to head-to-head / stats / player / table / statistical handlers; query-parsing helpers (team/season/competition/player extraction). |
| `server/server.go` | 329 | `Server` façade wrapping a `DataStore` with ~40 typed accessor methods (`GetTeamStats`, `GetPlayerByName`, `GetHeadToHead`, `GetBrasileiraoTable`, `GetStatisticalAnalysis`, …). |
| `server/server_test.go` | 648 | 36 `Test*` functions exercising loaders and query methods. |

## Data flow

CSV (`data/kaggle/*.csv`) → `DataStore.Load*` → per-competition `[]Match` slices +
`[]Player` → `getAllMatches()` merges slices → query methods aggregate → `QueryResult`
(struct with `Message` string + typed payload).

## Key observations

- The "MCP server" is nominal — the word appears only in comments. There is no MCP
  SDK, no JSON-RPC/stdio transport, and no tool/resource registration.
- Query routing is keyword string-matching over hardcoded team/player name lists, not
  MCP tool calls with typed arguments.
- Substantial logic is duplicated between `Server` (server.go) and `QueryEngine`
  (query.go): statistical analysis, biggest-wins, league-table and
  competition-membership each exist in two copies.
