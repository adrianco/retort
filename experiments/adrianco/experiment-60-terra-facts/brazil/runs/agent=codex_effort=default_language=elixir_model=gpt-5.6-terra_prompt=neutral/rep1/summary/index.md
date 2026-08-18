# Architecture Summary — brazilian_soccer_mcp

An Elixir OTP app (no external deps) that loads the six Kaggle CSVs into an
in-memory catalog and serves MCP tools over stdio (JSON-RPC 2.0).

## Modules

| Module | File | Role |
|--------|------|------|
| `BrazilianSoccerMcp.CLI` | `lib/brazilian_soccer_mcp/cli.ex` | escript `main/1` entrypoint; starts app, runs stdio loop |
| `BrazilianSoccerMcp.MCP` | `lib/brazilian_soccer_mcp/mcp.ex` | JSON-RPC dispatch: `initialize`, `tools/list`, `tools/call`, `resources/*`; 7 tools |
| `BrazilianSoccerMcp.Query` | `lib/brazilian_soccer_mcp/query.ex` | Pure query functions: matches, team_statistics, head_to_head, players, standings, competition_statistics |
| `BrazilianSoccerMcp.Catalog` | `lib/brazilian_soccer_mcp/catalog.ex` | CSV→normalized match/player maps; team-name & date normalization |
| `BrazilianSoccerMcp.Store` | `lib/brazilian_soccer_mcp/store.ex` | GenServer holding the lazily-loaded catalog |
| `BrazilianSoccerMcp.CSV` | `lib/brazilian_soccer_mcp/csv.ex` | Hand-rolled RFC-4180 CSV parser (quoted commas, BOM strip) |
| `BrazilianSoccerMcp.JSON` | `lib/brazilian_soccer_mcp/json.ex` | Hand-rolled JSON encode/decode |
| `BrazilianSoccerMcp.Application` | `lib/brazilian_soccer_mcp/application.ex` | Supervises the Store |

## Data flow

CLI/MCP `tools/call` → `Store.catalog()` (lazy `Catalog.load/1`, memoized) →
`Query.*` pure function → `JSON.encode` → MCP `content` text block.

## Tools exposed

`search_matches`, `team_statistics`, `compare_teams`, `search_players`,
`standings`, `competition_statistics`, `catalog_summary` — plus a
`brazilian-soccer://catalog` resource.

## Notable characteristics

- Zero runtime dependencies (CSV + JSON hand-rolled).
- Team keys strip state suffix (`-SP`) and accents for consistent matching.
- Aggregations override the 50-row display limit (limit=100_000) to avoid truncation.
- **Weakness:** tool `inputSchema` is `{"type":"object","additionalProperties":true}`
  with no declared `properties` — clients cannot discover arguments.
- **Weakness:** the competition filter is a substring match, so `"Brasileirão"`
  also matches the `"Brasileirão Historical"` source (double-counting overlapping seasons).
