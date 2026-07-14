# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/br_soccer_mcp_main.erl | escript entrypoint; picks data dir, starts server | `main/1` |
| src/br_soccer_mcp_server.erl | stdio JSON-RPC loop; reads lines, dispatches, writes responses | `start/0`, `start/1`, `process_line/2` |
| src/br_soccer_mcp_handler.erl | MCP protocol: initialize, tools/list, tools/call; 6 tool defs + formatters | `handle/2`, `encode_json/1`, `decode_json/1` |
| src/br_soccer_query.erl | Query engine: filters, team stats, head-to-head, standings, players, aggregates | `filter_by_team/2`, `filter_by_season/2`, `head_to_head/3`, `team_stats/2`, `search_players/2`, `compute_standings/1`, `biggest_matches/2`, `avg_goals/1` |
| src/br_soccer_data.erl | Loads the 6 Kaggle CSVs into maps; unifies match lists with competition tag | `load_all/1`, `all_matches/1`, `load_*/1` |
| src/br_soccer_csv.erl | Hand-rolled CSV parser (quoted fields), team-name normalization, date parsing | `parse_string/1`, `parse_line/1`, `normalize_team/1`, `parse_date/1` |
| src/br_soccer_mcp_app.erl | OTP application behaviour | `start/2`, `stop/1` |
| src/br_soccer_mcp_sup.erl | OTP supervisor (empty child specs) | `start_link/0`, `init/1` |
| src/br_soccer_mcp.app.src | App resource file (deps: kernel, stdlib, jsx) | — |
| test/br_soccer_csv_tests.erl | CSV parser unit tests | 15 test funcs |
| test/br_soccer_query_tests.erl | Query-engine unit tests | 13 test funcs |
| test/br_soccer_data_tests.erl | CSV-loading tests against real data/kaggle | 8 test funcs |
| test/br_soccer_mcp_handler_tests.erl | Handler / JSON-RPC dispatch tests | 8 test funcs |
| test/br_soccer_mcp_server_tests.erl | End-to-end process_line tests | 6 test funcs |
