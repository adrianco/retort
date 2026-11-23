# Architecture Summary

Objective-C (ARC) command-line MCP server, ~276 LOC across 3 source files, linking
Foundation + `libsqlite3`.

## Modules

- **`main.m`** — MCP transport + protocol. A `getline` loop over stdin reads one JSON-RPC
  2.0 message per line; `dispatch()` handles `initialize`, `ping`, `tools/list`,
  `tools/call`, and notifications (null-id → no response). Exposes a single tool,
  `query_soccer`, whose rich `description` documents the full schema so an LLM can author
  SQL. `tools/call` runs the SQL through `SoccerGraph` and returns `{rows, hasMore}` as JSON
  text; exceptions become MCP `isError` tool results.
- **`Graph.m` / `Graph.h`** — `SoccerGraph` data layer over an in-memory SQLite DB.
  - `readCSV` — a hand-rolled RFC-4180-ish parser (quoted commas, doubled quotes, embedded
    newlines, UTF-8 validation) streaming rows to a block.
  - `club()` / `club_key` SQL function — team-name normalisation (diacritic folding, state
    suffix stripping, alias map, homonym/state disambiguation) for consistent matching.
  - Ingest of all 6 CSVs into `raw_matches` + `players`; a consolidated `matches` table that
    de-duplicates overlapping league seasons across sources and back-fills missing scores;
    views `team_results` (both perspectives) and `standings` (computed points/W-D-L/goals);
    a `rivals` table for derby detection.
  - `query:` — prepares/executes read-only SELECTs with a SQL authorizer (denies writes &
    `load_extension`), a 4-second progress-handler deadline, and a 100-row page cap.

## Flow

stdin JSON-RPC → `dispatch` → `query_soccer` → `[SoccerGraph query:sql]` → SQLite (in-memory,
read-only authorizer) → JSON rows → stdout.

## Tests

`tests.py` (Python `unittest`) launches the compiled `./soccer-mcp` over real stdio and drives
5 scenarios: source/coverage counts, derby history + standings + team record, player
attributes/relationships, 20 sample-question SQL probes, and missing-scores/alias/paging plus
write-rejection and unknown-method error paths.
