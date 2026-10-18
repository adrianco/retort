# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.c | CLI entry: resolve data dir, load DB, serve MCP over stdio | `main()` |
| src/mcp.c | MCP JSON-RPC 2.0 server loop over stdin/stdout | `mcp_serve()` |
| src/query.c | The seven query tools + tools/list schema | `query_run()`, `query_tools_json()` |
| src/db.c | Loads/dedups the six CSVs into matches/teams/players | `db_load()`, `db_free()`, `db_find_team()` |
| src/csv.c | RFC 4180 CSV parser (quotes, CRLF, BOM) | `csv_parse()`, `csv_load()`, `csv_col()`, `csv_get()`, `csv_free()` |
| src/json.c | JSON parser + string escaping/quoting | `json_parse()`, `json_get()`, `json_free()`, `json_escape()`, `json_quote()` |
| src/util.c | Growable buffer, team-name normalization, date/int parsing | `Buf` ops, `normalize_name()`, `team_identity()`, `display_name()`, `name_contains()`, `parse_date()`, `parse_int()` |
| tests/test_unit.c | In-process GWT unit/behaviour tests over fixtures | `main()` — 119 assertions across 10 test functions |
| tests/test_mcp.sh | Protocol-level stdio tests of the server binary | 11 `expect` checks + reply-count check |

Headers (`src/*.h`) declare the above interfaces. Build artifacts under `bin/` are excluded.
