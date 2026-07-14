# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Library crate root; declares the five modules | `data`, `mcp`, `model`, `normalize`, `query` |
| src/main.rs | stdio binary: loads data, reads newline-delimited JSON-RPC, dispatches | `main()`, `resolve_data_dir()` |
| src/model.rs | Core domain types and date parsing | `Match`, `Player`, `Competition`, `MatchResult`, `parse_date()` |
| src/normalize.rs | Canonical team-name keys (loose + strict) | `normalize_team()`, `canonical_id()` |
| src/data.rs | CSV loaders for the 6 Kaggle datasets | `load_all_matches()`, `load_players()`, `parse_goal()` |
| src/query.rs | In-memory `Database` + all query/stat operations | `Database`, `MatchFilter`, `TeamRecord`, `HeadToHead`, `StandingRow` |
| src/mcp.rs | JSON-RPC 2.0 MCP server: tool defs + dispatch | `McpServer`, `handle_message()`, `call_tool()`, `tool_definitions()` |

Tests are colocated as `#[cfg(test)] mod tests` in every source module (62 `#[test]` functions total): data.rs (8), mcp.rs (14), model.rs (8), normalize.rs (10), query.rs (22).
