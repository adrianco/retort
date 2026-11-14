# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer/cli.ex | Escript entry point; sets UTF-8 stdio, loads data, runs the server | `main/1` |
| lib/mix/tasks/soccer.mcp.ex | Mix task wrapper to run the server (`mix soccer.mcp [dir]`) | `Mix.Tasks.Soccer.Mcp.run/1` |
| lib/brazilian_soccer/mcp/server.ex | JSON-RPC 2.0 stdio transport + pure protocol handler (initialize/ping/tools/list/tools/call) | `run/2`, `handle_line/1`, `handle/1` |
| lib/brazilian_soccer/tools.ex | MCP tool catalogue: 16 tool JSON-schema definitions and dispatch to Queries | `list/0`, `names/0`, `call/3` |
| lib/brazilian_soccer/queries.ex | Query/aggregation engine: matches, team stats, head-to-head, standings, brackets, rankings, summaries, players | `matches/2`, `team_stats/3`, `head_to_head/4`, `standings/3`, `rankings/2`, `summary/2`, `biggest_wins/3`, `derbies/2`, `bracket/3`, `players/2`, `team_profile/2`, `teams/2` |
| lib/brazilian_soccer/data.ex | Loads 6 CSVs into one knowledge base, normalises team names, merges duplicate fixtures; cached in `:persistent_term` | `get/0`, `default_dir/0`, `league?/1`, `competitions/0`, `files/0` |
| lib/brazilian_soccer/structs.ex | `Match` and `Player` struct definitions | `BrazilianSoccer.Match`, `BrazilianSoccer.Player` |
| lib/brazilian_soccer/team_names.ex | Team-name canonicalisation (state suffixes, accents, spelling variants) | module data + helpers |
| lib/brazilian_soccer/csv.ex | Small RFC-4180 CSV parser (quotes, escapes, CRLF, BOM) | `parse/1`, `parse_maps/1`, `read_maps!/1` |
| lib/brazilian_soccer/text.ex | Accent-insensitive normalisation; int/date parsing (ISO + Brazilian formats) | `normalize/1`, `to_int/1`, `parse_datetime/1`, `parse_date/1` |
| lib/brazilian_soccer/format.ex | Human-readable formatting of matches, records, standings, players | `match/1`, `match_list/3`, `record/1`, `standings/1`, `player/1`, `head_to_head/1` |
| test/data_test.exs | Data-loading scenarios (5 tests) | 5 test functions |
| test/queries_test.exs | Query/stats/player/performance scenarios (26 tests) | 26 test functions |
| test/mcp_test.exs | MCP protocol + ≥20 sample-question coverage (8 tests) | 8 test functions |
| test/unit_test.exs | CSV parser, date/number parsing, team-name normalisation (7 tests) | 7 test functions |
