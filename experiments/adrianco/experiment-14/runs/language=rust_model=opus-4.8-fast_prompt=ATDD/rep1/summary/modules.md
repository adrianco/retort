# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entrypoint; loads data, runs the stdio JSON-RPC read loop | `main()` |
| src/mcp.rs | MCP server: handshake, `tools/list`, `tools/call`, tool registry | `Server`, `Server::new`, `Server::handle` |
| src/tools.rs | The seven query capabilities exposed over MCP | `search_matches`, `team_record`, `head_to_head`, `search_players`, `league_standings`, `competition_stats`, `list_competitions`, `ToolOutput` |
| src/data.rs | Loads & de-duplicates the 5 match CSVs + FIFA players into in-memory `Vec`s | `DataStore`, `DataStore::load` |
| src/model.rs | Domain types for matches and players | `Match`, `Player`, `Match::new`, `Match::involves`, `Match::dedup_key` |
| src/normalize.rs | Accent folding, date parsing, competition-name canonicalization | `fold`, `display_team`, `parse_date`, `canonical_competition_query` |
| src/teams.rs | Curated alias table mapping club spellings to one canonical identity | `canonical`, `key`, `display`, `query_matches` |
| tests/acceptance.rs | 17 black-box acceptance tests driving the server over MCP | 17 `#[test]` functions |
| tests/common/mod.rs | Test harness: spawns the server binary, speaks JSON-RPC over stdio | `McpClient`, `McpClient::start`, `call`, `call_expecting_error` |

Unit tests live inline: `src/normalize.rs` (3) and `src/teams.rs` (3).
