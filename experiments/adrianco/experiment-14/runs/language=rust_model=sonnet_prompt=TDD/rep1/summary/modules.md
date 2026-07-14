# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Crate root, declares public modules | `models`, `data`, `query`, `mcp` |
| src/models.rs | Domain types + team-name normalization | `Competition`, `Match`, `Player`, `TeamStats`, `normalize_team_name()` |
| src/data.rs | CSV loaders for all 6 datasets + in-memory DB | `Database`, `Database::load_from_dir()`, `load_brasileirao()`, `load_copa_do_brasil()`, `load_libertadores()`, `load_extended()`, `load_historical()`, `load_players()` |
| src/query.rs | Query/aggregation logic over loaded data | `MatchFilter`, `search_matches()`, `head_to_head()`, `team_stats()`, `standings()`, `search_players()`, `goals_per_match()`, `home_win_rate()`, `biggest_wins()` |
| src/mcp.rs | MCP JSON-RPC server: tool definitions + dispatch | `tool_definitions()`, `handle_tool_call()`, `process_message()`, `JsonRpcRequest/Response` |
| src/main.rs | Binary entry point — stdin/stdout JSON-RPC loop | `main()`, `find_data_dir()` |

Tests are co-located as `#[cfg(test)] mod tests` in each of models.rs, data.rs, query.rs, mcp.rs (54 `#[test]` functions total). No separate `tests/` directory.
