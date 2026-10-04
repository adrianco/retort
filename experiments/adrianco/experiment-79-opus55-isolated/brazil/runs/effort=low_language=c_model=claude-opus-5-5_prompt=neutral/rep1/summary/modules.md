# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.c | Executable entry point; stdio MCP loop + one-shot `--call` mode | `main()` |
| src/mcp.c | MCP tool registry (15 tools) and JSON-RPC dispatch (initialize/ping/tools/list/tools/call) | `mcp_handle()`, `mcp_call_tool()` |
| src/soccer.c | Knowledge base: loads 6 CSVs, normalizes team names, all query engine functions | `db_load()`, `q_*` query functions |
| src/json.c | Minimal JSON parser and writer | `json_parse()`, `json_write()`, `json_get()`, `json_free()` |
| src/util.c | Growable string buffer, UTF-8 accent folding, date parsing, CSV loader | `sb_*`, `fold()`, `parse_date()`, `csv_load()` |
| src/soccer.h | DB/Team/Match/Params types and query prototypes | `DB`, `Params`, `QueryFn` |
| src/mcp.h | MCP server name/version macros and public API | `mcp_handle` decl |
| src/json.h | JSON value type (`JV`) and API | `JV`, `J_*` enum |
| src/util.h | Shared helper prototypes | `SB`, `CSV` |
| tests/test_soccer.c | BDD-style unit/integration tests (10 scenarios, 128 assertions) | `main()`, `test_*` functions |
| tests/test_stdio.sh | End-to-end stdio JSON-RPC protocol smoke test | shell script |
