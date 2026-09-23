# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/br_soccer/csv.ex | Minimal RFC4180 CSV parser (quoted fields, embedded commas, BOM strip) | `read_maps/1`, `parse/1` |
| lib/br_soccer/team.ex | Team-name normalization (canonical keys, aliases, state suffixes), rivalries, display names | `canonical/1`, `matches?/2`, `display/1`, `derby/2`, `ascii/1` |
| lib/br_soccer/data.ex | Loads the 6 Kaggle CSVs into normalized in-memory records (`:persistent_term`), cross-file dedup, date/int/competition parsing | `load/0`, `matches/0`, `players/0`, `parse_date/1`, `parse_competition/1`, `competition_name/1` |
| lib/br_soccer/query.ex | Queries + aggregates over matches/players (filter, head-to-head, records, standings, summaries, biggest wins, derbies, player search) | `matches/1`, `head_to_head/3`, `team_record/2`, `standings/2`, `best_records/1`, `summary/1`, `biggest_wins/1`, `players/1`, `players_by_club/1` |
| lib/br_soccer/tools.ex | 15 MCP tool definitions (JSON schemas) + text-formatting implementations | `definitions/0`, `call/2`, `fmt_match/1` |
| lib/br_soccer/mcp_server.ex | stdio JSON-RPC 2.0 MCP server loop (initialize / tools/list / tools/call / ping) | `main/0`, `handle_json/1`, `handle/1` |
| test/features_test.exs | BDD-style Given/When/Then scenarios over the real data | 26 tests |
| test/mcp_server_test.exs | JSON-RPC handshake, tools/list, tools/call, error codes | 5 tests |
| test/team_test.exs | Name normalization + CSV parsing edge cases | 4 tests |
| test/test_helper.exs | ExUnit bootstrap + `Data.load()` | (setup) |
