# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bsoccer_cli.erl | escript entry point + MCP stdio (newline-delimited JSON-RPC) transport loop | `main/1`, `serve/0` |
| src/bsoccer_mcp.erl | MCP / JSON-RPC 2.0 message dispatch and tool catalogue | `handle_message/1`, `tools/0`, `call_tool/2`, `server_info/0` |
| src/bsoccer_query.erl | Query + answer-formatting layer over the knowledge graph | `search_matches/1`, `head_to_head/1`, `team_record/1`, `standings/1`, `search_players/1`, `match_stats/1`, `data_summary/1` |
| src/bsoccer_data.erl | gen_server data loader; parses 6 CSVs into two protected ETS tables | `start_link/0,1`, `ensure_started/0,1`, `matches_table/0`, `players_table/0`, `stats/0` |
| src/bsoccer_csv.erl | Minimal RFC-4180 quote-aware CSV reader | `parse_file/1`, `parse/1`, `parse_file_as_maps/1`, `rows_as_maps/2` |
| src/bsoccer_util.erl | Team-name normalisation, accent folding, date/int/goal parsing | `team_key/1`, `clean_team/1`, `norm_key/1`, `fold_accents/1`, `parse_date/1`, `parse_int/1`, `parse_goal/1`, `trim/1` |
| src/bsoccer.app.src | OTP application resource file | `bsoccer` app |
| test/bsoccer_tests.erl | EUnit suite: pure-unit helpers + data-backed integration tests | 11 `*_test/0` + 13 generated `?_test` cases |
