# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entry: load datasets, serve MCP over stdin/stdout | `main()`, `serve()` |
| src/lib.rs | Crate root re-exporting the modules | `data`, `normalize`, `query`, `tools`, `mcp` |
| src/mcp.rs | JSON-RPC 2.0 / MCP protocol handling over stdio | `handle_line()`, `PROTOCOL_VERSION` |
| src/tools.rs | MCP tool definitions, arg parsing, text formatting | `definitions()`, `call()` |
| src/query.rs | Pure query layer over `Dataset` | `find_matches()`, `team_stats()`, `head_to_head()`, `standings()`, `league_stats()`, `search_players()` |
| src/data.rs | CSV loading, dedup, date/goal parsing, `Dataset` model | `Dataset::load()`, `Match`, `Player`, `Competition`, `parse_date()` |
| src/normalize.rs | Team-name folding/aliasing, accent folding | `team_key()`, `display_name()`, `fold()` |
| tests/bdd_queries.rs | Given/When/Then scenarios over the query layer on real data | 12 test functions |
| tests/mcp_protocol.rs | JSON-RPC request/response + stdio binary scenarios | 11 test functions |
| tests/common/mod.rs | Shared once-loaded dataset fixture | `dataset()` |
