# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazil_soccer_mcp.erl | Escript entry point: load data dir, start stdio server | `main/1` |
| src/bsm_mcp.erl | MCP server over stdio — newline-delimited JSON-RPC 2.0 dispatch | `run/0`, `handle_line/1` |
| src/bsm_tools.erl | MCP tool catalogue (JSON Schemas) + handlers → query filters → JSON | `definitions/0`, `call/2` |
| src/bsm_query.erl | Pure query/statistics over loaded matches and players | `find_matches/2`, `team_record/3`, `head_to_head/4`, `standings/2`, `league_stats/2`, `search_players/2`, `find_teams/2` |
| src/bsm_loader.erl | Load + normalise 6 Kaggle CSVs into match/player maps; de-dupe overlaps | `matches/1`, `players/1` |
| src/bsm_store.erl | Read-only dataset held in `persistent_term` | `load/1`, `matches/0`, `players/0` |
| src/bsm_team.erl | Team-name normalisation (suffixes, aliases, states), equality | `parse/1,2`, `same/2`, `key/1` |
| src/bsm_csv.erl | RFC 4180 CSV parser over binaries (quotes, CRLF, BOM) | `parse/1`, `rows_as_maps/1` |
| src/bsm_date.erl | Date normalisation (ISO + DD/MM/YYYY → ISO) | `parse/1` |
| src/bsm_text.erl | Accent/case folding, trim, substring, lenient int parse | `fold/1`, `trim/1`, `contains/2`, `parse_int/1` |
| include/bsm.hrl | Shared constants (`?SERIE_A`, `?DEFAULT_LIMIT`) | — |
| test/bsm_query_tests.erl | Query/stats tests over a hand-built fixture | 7 test generators |
| test/bsm_bdd_tests.erl | BDD acceptance tests against the real datasets | `feature_test_/0` (12 scenarios) |
| test/bsm_mcp_tests.erl | Protocol-level JSON-RPC request/response tests | `mcp_test_/0` (11 cases) |
| test/bsm_unit_tests.erl | Unit tests for CSV, text, team, date helpers | 4+ test generators |
