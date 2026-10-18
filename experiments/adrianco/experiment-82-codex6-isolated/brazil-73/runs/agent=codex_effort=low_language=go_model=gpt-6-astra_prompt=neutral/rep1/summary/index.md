# Architecture summary

*(Generated inline by `evaluate-run`; the standalone `run-summary` skill is not
registered in this session.)*

A single-package Go program (`package main`, module `brazilian-soccer-mcp`,
stdlib only — no external dependencies) implementing an MCP stdio server over a
small in-memory knowledge graph built from the six Kaggle CSVs.

## Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `main.go` | 215 | MCP transport: JSON-RPC 2.0 over newline-delimited stdio (`Serve`), `initialize`/`notifications/initialized` handshake with state gating, `tools/list`, `tools/call`, `ping`. Declares the 8 tool schemas (`toolsList`). `main()` loads the graph then serves. Logs kept off stdout. |
| `data.go` | 376 | Ingestion + graph build (`LoadGraph`, `readCSV`). Team-name normalization (`fold`, `teamKey`, accent folding, state-suffix handling, alias table), competition normalization, multi-format date parsing, and cross-source fixture reconciliation (adjacent-day merge by score/teams/competition, provenance retained per source). |
| `query.go` | 407 | Query engine + tool dispatch (`Graph.Call`). `FindMatches`/`FindPlayers` filters, `Record`/`Summary` aggregates, standings via `records`, head-to-head, statistics with seasonal trends, pagination (`page`), derby detection, cup-stage mapping, and `Query.validate`. |
| `soccer_test.go` | 390 | 14 tests + 1 benchmark, incl. a 24-case natural-language scenario table and an end-to-end MCP stdio test. |

## Interfaces / data model

- `Graph{ Matches, Players, Teams (adjacency), Rosters, Sources, Warnings }` — the knowledge graph.
- `Match` and `Player` carry a per-source `Attributes` map preserving raw rows (provenance).
- 8 MCP tools: `dataset_info`, `search_matches`, `search_players`, `team_profile`,
  `head_to_head`, `standings`, `competition_results`, `statistics`.

## Flow

`main` → `LoadGraph(dir)` reads 6 CSVs → normalizes/merges into `Graph` → `Serve`
reads JSON-RPC lines → `initialize` handshake → `tools/call` → `Graph.Call(name, Query)`
→ `Query.validate` then per-tool branch → JSON result wrapped as MCP `content`.
