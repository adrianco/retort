# Architecture summary — brazilian-soccer-mcp (erlang / opus-5.5)

A stdio MCP server (JSON-RPC 2.0) over the six Kaggle CSV datasets, built with
rebar3 + escript. No external dependencies (`deps = []`); uses OTP's built-in
`json` module.

## Modules

| Module | Role |
|--------|------|
| `src/brsoccer.erl` | escript entry point; stdio read loop, one JSON message per line. Loads data then `bs_mcp:handle_line/1` per line. |
| `src/bs_mcp.erl` | MCP/JSON-RPC layer: `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`. Handles batch arrays, notifications (no reply), parse/invalid-request/method-not-found error codes. Negotiates protocol version. |
| `src/bs_tools.erl` | 15 tool definitions with JSON input schemas + `call/2` dispatch and human-readable text rendering. Argument parsing/validation with typed errors. |
| `src/bs_query.erl` | Filtering + aggregation over matches/players: `matches/1`, `record/2,3`, `head_to_head/3`, `standings/1`, `league_stats/1`, `biggest_wins/2`, `rankings/4`, `team_competitions/1`, `derbies/1`, `players/1`, competition/stage/position parsing. |
| `src/bs_data.erl` | Loads 6 CSVs into `persistent_term`; row converters per file; team-name normalisation; multi-format date parsing; dedup of overlapping Serie A files; cup-final tagging; drop of mislabelled rows. |
| `src/bs_team.erl` | Team-name folding (accent/case), club-alias table, UF/homonym classification, rivalry table. |
| `src/bs_csv.erl` | RFC-4180 CSV parser (quotes, doubled quotes, CRLF, BOM). |

## Data flow

`brsoccer:main/1` → `bs_data:load/1` (reads `data/kaggle/*.csv` → `persistent_term`)
→ read loop → `bs_mcp:handle_line/1` → `bs_mcp:method/2` → `bs_tools:call/2` →
`bs_query:*` over the in-memory dedup'd match list + FIFA player list → rendered text
returned as MCP `tools/call` content.

## Datasets

All 6 files loaded (`bs_data:sources/0` asserts exact row counts:
brasileirao 4180, novo_brasileirao 6886, copa_do_brasil 1337, libertadores 1255,
br_football 10296, fifa_players 18207). Three files overlap on Serie A; a merged
dedup view (matches within 2 days, same competition/teams) is used by default.

## Tests

Three eunit suites: `bs_unit_tests` (CSV/date/team classification, no dataset),
`bs_mcp_tests` (JSON-RPC protocol scenarios), `bs_scenarios_tests` (33 BDD
Given/When/Then scenarios against the real datasets through the tool interface).
`All 76 tests passed` in the agent log; `test_coverage=1.0`.
