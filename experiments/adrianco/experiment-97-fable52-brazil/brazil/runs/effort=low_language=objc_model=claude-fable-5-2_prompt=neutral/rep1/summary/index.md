# Architecture summary — brazilian-soccer-mcp (objc)

Hand-rolled MCP (JSON-RPC 2.0) stdio server in ARC Objective-C over Foundation, no third-party deps. ~1,870 LOC across 6 source modules + 1 test file.

## Modules

| File | Role |
|------|------|
| `src/main.m` | Entry point. Locates data dir, loads store, serves MCP on stdin/stdout, or runs a one-shot `--call TOOL '{json}'`. |
| `src/BSCSV.{h,m}` | RFC-4180-ish CSV parser: quoted fields, embedded commas, escaped quotes, BOM, CRLF. |
| `src/BSTeamNames.{h,m}` | Team-name normalisation (state-suffix stripping, accent folding, canonical keys), derby table. |
| `src/BSDataStore.{h,m}` | Loads all 6 CSVs, merges overlapping fixtures, builds match/player models; query, standings, head-to-head, aggregate, biggest-wins, player-filter logic. |
| `src/BSTools.{h,m}` | 15 MCP tools: JSON schema + handler each, turning args into formatted text answers. |
| `src/BSMCPServer.{h,m}` | JSON-RPC dispatch: `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`, notifications; batch + error codes (-32600/-32601/-32602/-32700). |
| `tests/BSTests.m` | BDD (Given/When/Then) suite, 33 scenarios / 85 checks, incl. end-to-end over the compiled binary via stdio. |

## Flow

`main` → `BSDataStore initWithDataDirectory:` (parse CSV → normalise names → dedup/merge fixtures across files → sort) → `BSTools initWithStore:` (register 15 tools) → `BSMCPServer runWithInput:output:` (read line → JSON-RPC → tool handler → text content).

## Data model

- `BSMatch` (date, teams+keys, goals, competition, season, round/stage, merged sources, extra stats).
- `BSPlayer` (FIFA attributes + skills dict + canonical club key).
- `BSRecord` (aggregated W/L/D, goals, points, win-rate) computed on demand.

> `run-summary` skill not invoked directly; this is a lightweight inline equivalent.
