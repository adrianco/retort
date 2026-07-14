# Architecture Summary — brazilian-soccer-mcp (typescript)

> Generated inline by `evaluate-run` (the standalone `run-summary` skill was not
> invocable in this session). Concise module map only.

## Layered design

```
index.ts ──> data.ts ──> loader.ts ──> normalize.ts   (load + canonicalize CSVs)
   │            └──> store.ts (SoccerStore: in-memory queries)
   └──> server.ts (MCP adapter) ──> tools.ts (tool defs + dispatch) ──> format.ts
```

| Module | Responsibility |
|--------|----------------|
| `src/index.ts` | Entrypoint. Boots the MCP server over stdio; logs load diagnostics to stderr. |
| `src/data.ts` | `resolveDataDir()` + `createStore()` — wires loaders into a `SoccerStore`. |
| `src/loader.ts` | Six per-file CSV loaders → normalized `Match`/`Player`; cross-source `dedupeMatches`. |
| `src/normalize.ts` | Team-name canonicalization, diacritic stripping, multi-format date/number parsing. |
| `src/store.ts` | `SoccerStore` — pure synchronous query engine: match search, head-to-head, team records, computed standings, competition stats, player search. |
| `src/tools.ts` | Declares 7 MCP tools + `callTool` dispatcher (decoupled from transport for testing). |
| `src/server.ts` | Thin MCP protocol adapter (`ListTools`/`CallTool`). |
| `src/format.ts` | Text renderers matching the spec's example answer formats. |
| `src/types.ts` | `Match`, `Player`, `Competition`, `Outcome` domain types. |

## Notable design choices

- **Transport-decoupled tool layer.** `callTool(store, name, args)` is pure and
  unit-tested directly; `server.ts` only translates protocol ↔ functions.
- **Cross-source dedup.** The same Série A fixtures appear in up to three files;
  `dedupeMatches` keys on competition+season+home+away and keeps the richest
  record, preventing double-counted standings/stats.
- **Canonicalization everywhere.** User queries and CSV rows pass through the
  same `canonicalTeam`, so "São Paulo-SP", "Sao Paulo", "São Paulo" collide.

## Tools exposed

`find_matches`, `head_to_head`, `team_record`, `league_standings`,
`competition_stats`, `search_players`, `list_competitions`.
