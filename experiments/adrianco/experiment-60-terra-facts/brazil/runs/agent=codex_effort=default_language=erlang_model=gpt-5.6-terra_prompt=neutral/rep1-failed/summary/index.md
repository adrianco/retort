# Architecture Summary — Brazilian Soccer MCP (Erlang)

A self-contained stdio JSON-RPC MCP server over six Brazilian-soccer CSVs. ~211 LOC across 5 source modules + 1 test module, no external deps (`{deps, []}`).

## Modules

| Module | Role |
|--------|------|
| `soccer_mcp` | Server loop + MCP protocol. `main/1` reads a data dir, loads data once, then loops on stdin lines. Handles `initialize`, `tools/list`, `tools/call`. `tools/0` registers 6 tools. `filters/1` extracts typed arguments from the request line. |
| `soccer_data` | Loading + normalization. `load/1` reads the 5 match CSVs (each tagged with a competition atom) and `fifa_data.csv` into `#{matches => [...], players => [...]}`. `normalize_team/1` strips `-SP`-style state suffixes; `normalize_text/1` lowercases + folds Portuguese accents; `to_int/1` coerces numeric strings. |
| `soccer_query` | Query engine. `matches/2` (team/opponent/competition/season/date-range filter), `team_stats/3` (W/D/L + goals for/against), `head_to_head/3`, `players/2` (name/nationality/club/position filter, sorted by overall), `standings/3` (points table computed from results), `biggest_wins/2`, `answer/2` (minimal NL router). |
| `soccer_csv` | RFC-4180-style line parser (handles quoted fields, embedded commas, escaped `""`). |
| `soccer_json` | Hand-rolled JSON encoder (maps/lists/atoms/ints/floats/binaries, unicode + control-char escaping). Encode-only. |

## Data flow

`bin/brazilian_soccer_mcp` (escript) → `soccer_mcp:main/1` → `soccer_data:load/1` (CSV → normalized match/player maps, once at startup) → loop: read stdin line → `soccer_mcp:handle/2` → `soccer_query:*` → `soccer_json:encode/1` → stdout.

## Tests

`test/soccer_query_tests.erl` — 8 EUnit tests over an in-memory fixture: team-name normalization, cross-suffix derby matching, team record, head-to-head, player filter, standings ordering, date-range filter, and MCP `initialize` handling. No skips. `test_coverage=1.0` (build + all tests pass).

## Notes

- Request field extraction is regex-based rather than a real JSON decode (see findings F1).
- No module named for the app exposes a zero-arity `main`/`run`, so retort's factual/runtime probes could not auto-invoke the server (findings F2); the server itself is functional via the escript wrapper.
