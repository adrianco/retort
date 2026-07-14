# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer/application.ex | OTP application; starts the Store under a supervisor | `start/2` |
| lib/brazilian_soccer/store.ex | Holds loaded dataset in `:persistent_term` for lock-free reads | `start_link/1`, `matches/0`, `raw_matches/0`, `players/0`, `put/1` |
| lib/brazilian_soccer/loader.ex | Reads & normalises the six Kaggle CSVs into Match/Player collections; dedupes | `load/1`, `resolve_competition/1`, `competition_keys/0`, `competition_display/1` |
| lib/brazilian_soccer/normalize.ex | Pure helpers: team-name keys, accent folding, multi-format dates, lenient ints | `team_key/1`, `team_display/1`, `fold/1`, `parse_date/1`, `parse_int/1` |
| lib/brazilian_soccer/match.ex | Match struct + serialisation/predicates | `to_map/1`, `involves?/2`, `scored?/1` |
| lib/brazilian_soccer/player.ex | Player struct + serialisation | `to_map/1` |
| lib/brazilian_soccer/matches.ex | Match-finding by team/opponent/venue/competition/season/date range | `find/1` |
| lib/brazilian_soccer/teams.ex | Team W/D/L records and head-to-head aggregates | `record/2`, `head_to_head/3` |
| lib/brazilian_soccer/players.ex | FIFA player search and single-player lookup | `search/1`, `get/1`, `to_maps/1` |
| lib/brazilian_soccer/competitions.ex | Season standings from match results; competitions list/for-team | `standings/2`, `list_all/0`, `for_team/1`, `authoritative_matches/2` |
| lib/brazilian_soccer/statistics.ex | Aggregate stats: avg goals, home/away/draw rates, biggest wins | `competition_stats/2` |
| lib/brazilian_soccer/mcp/server.ex | JSON-RPC 2.0 MCP entry point (initialize, tools/list, tools/call) | `handle_json/1`, `handle/1` |
| lib/brazilian_soccer/mcp/tools.ex | Tool catalogue + handlers mapping arguments to domain queries | `specs/0`, `names/0`, `call/2` |
| lib/brazilian_soccer/mcp/stdio.ex | Newline-delimited JSON-RPC transport over stdin/stdout | `run/0` |
| lib/brazilian_soccer/mcp/format.ex | Human-readable text renderings of query results | `matches/1`, `head_to_head/1`, `team_record/1`, `players/1`, `player/1`, `standings/1`, `statistics/1` |
| lib/brazilian_soccer/cli.ex | escript entry (MCP stdio server launcher) | `main/1` |
| test/support/mcp_client.ex | Test-only client driving the SUT only through the MCP protocol | `request/1`, `initialize/0`, `list_tools/0`, `call/2`, `call_raw/2`, `call_text/2` |
| test/acceptance/protocol_test.exs | MCP handshake, tool discovery, error handling | 5 tests |
| test/acceptance/match_queries_test.exs | Category 1: match queries via `find_matches` | 6 tests |
| test/acceptance/team_queries_test.exs | Category 2: team records & head-to-head | 4 tests |
| test/acceptance/player_queries_test.exs | Category 3: player search & lookup | 7 tests |
| test/acceptance/competition_queries_test.exs | Category 4: standings & competition lists | 4 tests |
| test/acceptance/statistics_test.exs | Category 5: aggregate statistics | 4 tests |
| test/test_helper.exs | Starts ExUnit and the application (loads data once) | — |
