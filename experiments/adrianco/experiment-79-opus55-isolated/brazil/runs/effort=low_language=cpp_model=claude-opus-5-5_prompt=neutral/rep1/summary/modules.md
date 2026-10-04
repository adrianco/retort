# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer.hpp | Data model + query API (Database, Match, Player, filters, records) | `soccer::Database` |
| src/soccer.cpp | CSV parsing, team-name/date normalization, dedup, all queries | `Database::load`, `findMatches`, `teamRecord`, `headToHead`, `standings`, `compStats`, `findPlayers` |
| src/mcp_server.hpp | MCP server class declaration | `mcp::Server` |
| src/mcp_server.cpp | 15 tool handlers + JSON-RPC 2.0 dispatch (initialize/tools.list/tools.call) | `handle`, tool table |
| src/json.hpp | Minimal JSON value + parser/serializer | `Value` |
| src/main.cpp | Entrypoint: data-dir resolution, stdio loop, `--call` one-shot | `main` |
| tests/test_soccer.cpp | Given/When/Then scenarios against real data | 17 scenarios, 56 assertions |

## Tools exposed (15)

`search_matches`, `head_to_head`, `team_stats`, `standings`, `team_rankings`,
`biggest_wins`, `competition_stats`, `compare_seasons`, `derbies`, `search_players`,
`player_details`, `club_player_summary`, `team_profile`, `list_teams`, `dataset_info`.
