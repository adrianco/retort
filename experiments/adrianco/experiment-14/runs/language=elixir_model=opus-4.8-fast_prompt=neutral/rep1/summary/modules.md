# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/br_soccer.ex | Thin facade over the query modules (the programmatic API behind the MCP server) | `search_matches/1`, `head_to_head/3`, `team_record/2`, `standings/2`, `search_players/1`, `stats_summary/1`, `last_match/2` |
| lib/br_soccer/application.ex | OTP application — starts the `Repo` supervision tree | `start/2` |
| lib/br_soccer/repo.ex | In-memory store; parses CSVs once, caches via `:persistent_term` | `matches/0`, `players/0`, `team_keys/0`, `put_data/1`, `reload/0` |
| lib/br_soccer/loader.ex | Loads + normalises the six Kaggle CSVs into `Match`/`Player` structs, de-dups overlapping fixtures | `load_all/1`, `load_matches/1`, `load_players/1`, `parse_date/1`, `to_int/1` |
| lib/br_soccer/csv.ex | Dependency-free RFC 4180 CSV parser | `parse_file/1`, `parse_string/1`, `parse_rows/1` |
| lib/br_soccer/match.ex | Normalised match struct + result helpers | `%Match{}`, `scored?/1`, `result/1` |
| lib/br_soccer/player.ex | Normalised FIFA player struct | `%Player{}` |
| lib/br_soccer/team_name.ex | Team-name normalisation (accent/variation folding) | `key/1`, `display/1`, `clean/1`, `same?/2`, `deaccent/1` |
| lib/br_soccer/competition.ex | Competition identifiers, display names, free-text parsing | `name/1`, `parse/1`, `all/0` |
| lib/br_soccer/matches.ex | Match filtering/search + head-to-head + competitions-for-team | `search/1`, `search_with_total/1`, `head_to_head/3`, `competitions_for/1` |
| lib/br_soccer/teams.ex | Team W/D/L records, rankings, top scorers, biggest wins | `record/2`, `rankings/1`, `top_scoring_teams/1`, `biggest_wins/1` |
| lib/br_soccer/players.ex | FIFA player search + Brazilian-club squad grouping | `search/1`, `brazilians/1`, `brazilians_at_brazilian_clubs/1` |
| lib/br_soccer/competitions.ex | League standings/relegation computed from match results | `standings/2`, `champion/2`, `relegated/2`, `seasons/1`, `chosen_source/2` |
| lib/br_soccer/stats.ex | Aggregate stats over filtered match sets | `summary/1`, `compare_seasons/3` |
| lib/br_soccer/format.ex | Renders query results as human-readable text for tool replies | `matches/3`, `head_to_head/1`, `record/2`, `standings/2`, `players/2`, `player_card/1` |
| lib/br_soccer/mcp/server.ex | JSON-RPC 2.0 / MCP stdio transport; pure `handle_message/1` + `serve/0` loop | `handle_message/1`, `serve/0` |
| lib/br_soccer/mcp/tools.ex | MCP tool catalogue + dispatch (15 tools wrapping the queries) | `list/0`, `call/2` |
| lib/br_soccer/mcp/cli.ex | Escript / `mix run` entry point; `--ask` one-shot mode | `main/1` |
| test/integration_test.exs | End-to-end tests against the real Kaggle CSVs | 11 tests |
| test/queries_test.exs | Query-module unit tests (fixtures) | 16 tests |
| test/mcp_test.exs | MCP protocol + tool dispatch tests | 14 tests |
| test/csv_test.exs | CSV parser tests | 6 tests |
| test/loader_test.exs | Date/number parsing + loader tests | 4 tests |
| test/team_name_test.exs | Name-normalisation tests | 7 tests |
| test/support/fixtures.ex | Shared in-memory match/player fixtures | `BrSoccer.Fixtures` |
