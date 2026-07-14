# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer.ex | Top-level convenience entry / moduledoc | `BrazilianSoccer` |
| lib/brazilian_soccer/csv.ex | CSV parser → list of header-keyed row maps | `parse_to_maps/1` |
| lib/brazilian_soccer/data_loader.ex | Read Kaggle CSVs into normalized structs, dedup | `load!/1`, `from_brasileirao/1`, `from_cup/1`, `from_libertadores/1`, `from_br_football/1`, `from_historical/1`, `players_from_fifa/1`, `dedup_matches/1` |
| lib/brazilian_soccer/dataset.ex | In-memory matches + players collection | `Dataset.new/2`, `%Dataset{}` |
| lib/brazilian_soccer/match.ex | Match struct + helpers (winner, involves?, dates) | `Match.new/1`, `winner/1`, `involves?/2`, `parse_date/1`, `total_goals/1` |
| lib/brazilian_soccer/player.ex | FIFA player struct + row mapping | `Player.from_row/1`, `brazilian?/1` |
| lib/brazilian_soccer/team_name.ex | Team-name normalization / base-key matching | `clean/1`, `base/1` |
| lib/brazilian_soccer/queries/matches.ex | Match search (team/comp/season/date), head-to-head | `find/2`, `head_to_head/3`, `sort_recent/1` |
| lib/brazilian_soccer/queries/teams.ex | W/L/D record, goals, win rate, compare | `record/3`, `compare/3` |
| lib/brazilian_soccer/queries/players.ex | Player search/filter, by-club summary | `search/2`, `by_club/2` |
| lib/brazilian_soccer/queries/competitions.ex | Standings computed from matches, seasons | `standings/3`, `champion/3`, `seasons/2`, `competitions/1` |
| lib/brazilian_soccer/queries/stats.ex | Aggregate stats, biggest wins, best records | `summary/2`, `biggest_wins/2`, `best_record/3` |
| lib/brazilian_soccer/queries/source.ex | Per-(competition,season) authoritative-source dedup | `primary_per_season/1` |
| lib/brazilian_soccer/mcp/server.ex | JSON-RPC 2.0 / MCP request dispatch (pure) | `handle/2` |
| lib/brazilian_soccer/mcp/tools.ex | MCP tool registry + dispatcher (10 tools) | `list/0`, `call/3` |
| lib/brazilian_soccer/mcp/format.ex | Human-readable formatting of query results | `matches/2`, `record/2`, `standings/2`, `players/1`, `head_to_head/1`, `percent/1` |
| lib/brazilian_soccer/mcp/cli.ex | stdio transport / escript entry point | `main/1`, `process_line/2` |
| test/ (15 files) | ExUnit suites for every lib module | 91 tests, 36 describe blocks |
| test/support/fixtures.ex | Shared test dataset fixtures | fixture helpers |
