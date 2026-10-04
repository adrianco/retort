# Modules

Surface: an Elixir MCP (Model Context Protocol) server exposing a stdio JSON-RPC
knowledge-graph interface over six Kaggle CSV datasets of Brazilian soccer
(Brasileirão, Copa do Brasil, Copa Libertadores matches and the FIFA player
database), answering natural-language-style queries about matches, teams, players,
competitions and statistics via a set of MCP tools.

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer/cli.ex | Escript entry point; sets data dir, loads store, runs the stdio server | `main/1` |
| lib/brazilian_soccer/mcp/server.ex | MCP JSON-RPC 2.0 over stdio; dispatches initialize/ping/tools.list/tools.call | `run/2`, `handle_line/1`, `handle/1` |
| lib/brazilian_soccer/mcp/tools.ex | 14 MCP tool definitions (inputSchemas) and their implementations + text formatting | `list/0`, `call/2`, `match_text/1` |
| lib/brazilian_soccer/queries.ex | Match/team/competition queries over the unified match list: search, records, standings, rankings, summaries, derbies | `matches/1`, `team_stats/2`, `head_to_head/3`, `standings/2`, `rankings/2`, `summary/1`, `biggest_wins/2`, `derbies/1`, `compare_seasons/3`, `team_ref/1` |
| lib/brazilian_soccer/players.ex | Queries over the FIFA player dataset: search by name/nationality/club/position, group by club | `search/1`, `by_club/1` |
| lib/brazilian_soccer/loader.ex | Loads the six CSVs into unified match/player structs; merges duplicate fixtures; labels cup stages | `load/1`, `files/0`, `competitions/0` |
| lib/brazilian_soccer/teams.ex | Team-name normalisation to key/state/display name; aliases, state disambiguation, derby rivalries | `resolve/2`, `same?/3`, `derby_name/2`, `brazilian_club?/1`, `derbies/0` |
| lib/brazilian_soccer/store.ex | Holds loaded datasets in `:persistent_term`; lazy load, data-dir resolution | `data/0`, `matches/0`, `players/0`, `load/1`, `data_dir/0` |
| lib/brazilian_soccer/match.ex | `%Match{}` struct unified across source files | `Match` struct, `played?/1` |
| lib/brazilian_soccer/csv.ex | Minimal RFC 4180 CSV parser (quotes, commas, CRLF, BOM) | `parse/1`, `parse_maps/1` |
| lib/brazilian_soccer/text.ex | Text helpers: accent folding, date parsing, int parsing, blank check | `fold/1`, `parse_date/1`, `parse_int/1`, `blank?/1` |
| lib/mix/tasks/soccer.mcp.ex | Mix task `mix soccer.mcp [DATA_DIR]` to run the server | `run/1` |
| config/config.exs | Routes logger to stderr (stdout reserved for JSON-RPC) | (config) |
| test/queries_test.exs | BDD tests over loading, match/team/competition/player queries, stats | 30 test functions |
| test/mcp_server_test.exs | MCP protocol tests + 22 sample-question scenarios + per-tool smoke test | 29 test functions |
| test/csv_and_text_test.exs | CSV parsing, date/number formats, team normalisation, derbies | 8 test functions |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start()` |

No external dependencies (`deps: []`); uses only stdlib including the built-in `JSON` module.
