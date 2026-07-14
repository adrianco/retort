# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entrypoint; stdio JSON-RPC loop, data-dir discovery, tool dispatch | `main()`, `process_request()`, `handle_tool_call()` |
| src/mcp.rs | JSON-RPC request/response types + MCP tool definitions & server info | `JsonRpcRequest`, `JsonRpcResponse`, `tool_definitions()`, `server_info()` |
| src/data.rs | CSV loaders for all 6 datasets; `Match`/`Player` models; team-name normalization | `Database::load()`, `Match`, `Player`, `normalize_team_name()`, `team_matches()` |
| src/tools.rs | Query implementations behind the 8 MCP tools + 12 unit tests | `search_matches()`, `team_stats()`, `head_to_head()`, `search_players()`, `season_standings()`, `biggest_wins()`, `competition_stats()`, `top_scoring_teams()` |

Tests live inline: 3 `#[test]` in `src/data.rs`, 12 in `src/tools.rs` (15 total).
