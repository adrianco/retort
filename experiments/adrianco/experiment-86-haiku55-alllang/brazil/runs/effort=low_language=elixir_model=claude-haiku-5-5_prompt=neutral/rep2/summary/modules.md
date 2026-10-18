# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/soccer_mcp/cli.ex | Escript entry point; loads data then serves JSON-RPC over stdio | `main/1`, `serve/3` |
| lib/soccer_mcp/server.ex | JSON-RPC 2.0 / MCP method dispatch (`initialize`, `tools/list`, `tools/call`, `ping`) | `handle_line/2`, `handle/2` |
| lib/soccer_mcp/tools.ex | The six MCP tool schemas and argument handling/dispatch | `definitions/0`, `call/3` |
| lib/soccer_mcp/query.ex | Pure queries over the store: match filters, records, standings, averages, rankings, player search | `find_matches/2`, `record/2`, `head_to_head/4`, `standings/1`, `averages/1`, `biggest_wins/2`, `venue_ranking/3`, `players/2` |
| lib/soccer_mcp/store.ex | Loads all six CSVs into one match list + player list; de-dupes overlapping matches; labels cup finals | `load/1`, `parse_match/3`, `team_keys/1` |
| lib/soccer_mcp/match.ex | Normalized match struct and helpers (team involvement, goals-for/against, competition canonicalization) | `new/8`, `canonical_competition/1`, `involves?/2`, `goals_for_against/2`, `competitions/0` |
| lib/soccer_mcp/player.ex | FIFA player struct and row parsing | `from_row/1` |
| lib/soccer_mcp/team.ex | Team-name normalization: state suffixes, accents, full-name aliases, whole-word matching | `key/1`, `display/1`, `state/1`, `compatible_states?/2`, `matches?/2` |
| lib/soccer_mcp/parse.ex | Field parsers: ISO/dotted/Brazilian dates, integers, accent folding | `date/1`, `int/1`, `fold/1` |
| lib/soccer_mcp/csv.ex | Minimal RFC 4180 CSV reader (BOM, CRLF, quoted fields, doubled quotes) | `parse/1`, `parse_file/1` |
| lib/soccer_mcp/format.ex | Renders query results as plain text per the spec's answer formats | `match_line/1`, `match_list/2`, `record_summary/2`, `head_to_head_summary/3`, `standings_table/3`, `averages/2`, `biggest_wins/1`, `venue_ranking/2`, `players/1` |
| test/soccer/*.exs | 10 test files: 71 tests + 7 doctests, incl. `real_data_test.exs` against data/kaggle | see interfaces.md |
