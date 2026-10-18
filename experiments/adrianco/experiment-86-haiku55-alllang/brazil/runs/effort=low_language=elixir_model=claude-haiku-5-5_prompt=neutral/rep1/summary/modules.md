# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer/cli.ex | Escript/`mix run` entry point; reads newline-delimited JSON-RPC from stdin, writes responses to stdout, logs to stderr | `main/1` |
| lib/brazilian_soccer/server.ex | JSON-RPC 2.0 / MCP dispatch (`initialize`, `ping`, `tools/list`, `tools/call`); pure request→response | `handle_line/2`, `handle/2` |
| lib/brazilian_soccer/tools.ex | MCP tool descriptors + handlers; validates args, calls `Queries`, formats human-readable text | `list/0`, `call/3` |
| lib/brazilian_soccer/queries.ex | Pure query layer over matches/players: find, record, head-to-head, standings, league stats, biggest wins, ranking, player search | `find_matches/2`, `team_record/3`, `head_to_head/4`, `standings/2`, `league_stats/2`, `biggest_wins/2`, `ranking/3`, `search_players/2`, `ranking_metrics/0` |
| lib/brazilian_soccer/data.ex | Loads the 6 Kaggle CSVs into `Match`/`Player` structs; merges & de-duplicates the 5 match files | `load/1` |
| lib/brazilian_soccer/csv.ex | Minimal RFC-4180 CSV reader (BOM, CRLF, quoted fields) | `parse_rows/1`, `parse_with_headers/1` |
| lib/brazilian_soccer/normalize.ex | Team-name folding, display-name cleanup, alias table, integer parsing | `fold/1`, `display_name/1`, `team_key/1`, `integer/1` |
| lib/brazilian_soccer/dates.ex | Parses ISO and Brazilian (DD/MM/YYYY) date strings | `parse/1` |
| lib/brazilian_soccer/match.ex | `Match` struct; derives display names + normalized keys | `new/1` |
| lib/brazilian_soccer/player.ex | `Player` struct (FIFA record) | (struct only) |
| test/brazilian_soccer/queries_test.exs | Query-layer tests (26 tests) | 26 test functions |
| test/brazilian_soccer/server_test.exs | MCP protocol / tool-call tests (16 tests) | 16 test functions |
| test/brazilian_soccer/data_test.exs | Dataset loading incl. real-data check (11 tests) | 11 test functions |
| test/brazilian_soccer/normalize_test.exs | Name-normalization tests (9 tests) | 9 test functions |
| test/brazilian_soccer/csv_test.exs | CSV parser tests (8 tests) | 8 test functions |
| test/brazilian_soccer/dates_test.exs | Date-parsing tests (3 tests) | 3 test functions |

Zero external dependencies (`deps: []`); uses the Elixir standard library's built-in `JSON` module and a hand-written CSV parser.
