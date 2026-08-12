# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Crate root; declares modules and re-exports the public API | `mcp`, `model`, `normalize`, `store` mods; `McpServer`, `SoccerStore`, `model::*` |
| src/main.rs | Binary entrypoint; loads data, runs a JSON-RPC stdio loop (or `--check` counts dump) | `main()`, `arguments()` |
| src/mcp.rs | MCP protocol surface: JSON-RPC dispatch, tool definitions, tool-call routing, arg parsing | `McpServer::new`, `McpServer::handle`, `McpServer::store`, `tool_definitions()` |
| src/model.rs | Data types for matches, players, stats, filters, and serialized results | `MatchRecord`, `Player`, `DatasetCounts`, `TeamStats`, `HeadToHead`, `Standing`, `MatchFilter`, `CompetitionStats` |
| src/normalize.rs | Accent folding, team-name canonicalization, competition keys, multi-format date parsing | `fold()`, `team_key()`, `team_matches()`, `competition_key()`, `display_competition()`, `parse_date()` |
| src/store.rs | CSV loading for all 6 datasets, fixture deduplication, and every query function | `SoccerStore::load`, `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, `competition_statistics`, `biggest_wins`, `team_overview`, `format_matches()` |
| tests/behavior.rs | BDD-style integration tests over the loaded datasets | 10 test functions |

Unit tests are also embedded via `#[cfg(test)]`: 3 in `src/normalize.rs`, 2 in `src/mcp.rs`.

Total: ~1,579 LOC across 6 source files + 1 integration test file.
