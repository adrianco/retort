# Architecture summary — brazilian-soccer MCP (C)

Three source files (~330 LOC C + 105 LOC Python tests). An in-memory SQLite
database fronted by a single-tool MCP server over newline-delimited JSON-RPC on
stdio.

## Modules

| File | Role |
|------|------|
| `soccer.h` | Shared declarations: global `sqlite3 *db`, `fail`/`run`/`prepare` helpers, `load_data`. |
| `data.c` | CSV ingestion + schema build. Streaming RFC-4180-ish CSV splitter (`record`), per-file `import` that infers a NUMERIC column per header, a `team_key()` SQL UDF that normalizes/aliases club names (accent-folding, state-suffix stripping, alias table), and `load_data` which imports the 6 CSVs into raw tables (`league`,`cup`,`libertadores`,`extended`,`historical`,`players`) then derives `reports`, `matches`, and the `appearances`/`standings`/`derbies` views. |
| `server.c` | MCP protocol + query engine. `main` opens `:memory:`, loads data, sets `query_only`, and loops over stdin dispatching JSON-RPC. `dispatch` uses a single prepared `json_extract` statement to parse each request. Handles `initialize`, `ping`, `tools/list`, `tools/call`. The one tool `query_soccer` takes a `sql` string and runs it through `query`, which enforces a SELECT-only authorizer, a VM-op progress budget, 200-row cap, and emits `{columns,rows,truncated}` JSON. |
| `test_soccer.py` | 6 `unittest` scenarios driving the compiled binary over stdio: discovery, source row-count coverage, match questions, team statistics/standings, player relationships, and error-recovery/pagination. |

## Interface / data flow

client → JSON-RPC line → `dispatch` (json_extract parse) → `tools/call query_soccer`
→ `query(sql)` → SQLite (authorizer + budget) → JSON `{columns,rows,truncated}`
wrapped in MCP `content[].text`.

## Design note

Rather than N discrete MCP tools (one per capability), the server exposes a
single read-only SQL endpoint plus a rich schema and a `tools/list` description
that documents the tables/columns. Every required capability (team/date/
competition match filters, W/L/D records, standings, player search, head-to-head,
aggregate stats) is reachable as a SELECT and is exercised by the test suite.
