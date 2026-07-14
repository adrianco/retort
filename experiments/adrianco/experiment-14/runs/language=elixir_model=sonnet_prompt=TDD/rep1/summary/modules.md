# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer.ex | CLI/escript entrypoint that starts the app and runs the MCP stdio loop | `main/1` |
| lib/brazilian_soccer/application.ex | OTP application supervisor; starts DataStore | `start/2` |
| lib/brazilian_soccer/data_store.ex | GenServer + ETS tables holding matches/players; loads CSVs on init | `matches/0`, `players/0`, `start_link/1` |
| lib/brazilian_soccer/data_loader.ex | Pure CSV row parsers + team-name/date/int normalization | `normalize_team_name/1`, `parse_brasileirao_row/1`, `parse_cup_row/1`, `parse_libertadores_row/1`, `parse_historico_row/1`, `parse_br_football_row/1`, `parse_player_row/1` |
| lib/brazilian_soccer/queries/matches.ex | Match search/filter functions over the store | `search_by_team/1`, `search_by_teams/2`, `search_by_competition/1`, `search_by_season/1`, `search_by_team_and_season/2`, `search_by_date_range/2`, `head_to_head_stats/2`, `biggest_wins/1` |
| lib/brazilian_soccer/queries/teams.ex | Team aggregates: records, standings, stats | `team_record/2`, `competition_standings/2`, `average_goals_per_match/1`, `home_win_rate/0`, `top_scoring_teams/3`, `best_away_teams/1` |
| lib/brazilian_soccer/queries/players.ex | FIFA player search/filter | `search_by_name/1`, `search_by_nationality/1`, `search_by_club/1`, `search_by_position/1`, `top_rated/2`, `players_by_club_with_nationality/2` |
| lib/brazilian_soccer/mcp/tools.ex | MCP tool schema definitions + `call/2` dispatch + response formatting | `definitions/0`, `call/2` |
| lib/brazilian_soccer/mcp/server.ex | JSON-RPC 2.0 / MCP protocol handler + stdio loop | `handle_request/1`, `run/0` |
| test/brazilian_soccer_test.exs | Top-level smoke test | 1 test |
| test/brazilian_soccer/data_loader_test.exs | CSV parsing / normalization tests | 10 tests |
| test/brazilian_soccer/queries/matches_test.exs | Match query tests | 15 tests |
| test/brazilian_soccer/queries/players_test.exs | Player query tests | 12 tests |
| test/brazilian_soccer/queries/teams_test.exs | Team aggregate tests | 9 tests |
| test/brazilian_soccer/mcp/server_test.exs | MCP protocol + tool-call tests | 11 tests |
