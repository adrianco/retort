# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazilian_soccer_mcp.erl | Escript entry point; loads dataset once, serves over stdio | `main/1` |
| src/bs_mcp.erl | MCP server: newline-delimited JSON-RPC 2.0 over stdio | `run/1`, `handle_line/2` |
| src/bs_tools.erl | MCP tool catalogue (7 tools), arg handling, result formatting | `list/0`, `call/3` |
| src/bs_query.erl | Pure query functions over the loaded dataset | `resolve_team/2`, `search_matches/2`, `team_stats/3`, `head_to_head/3`, `standings/2`, `aggregate/2`, `search_players/2`, `brazilian_club_summary/1` |
| src/bs_data.erl | Loads 5 match CSVs + FIFA players, dedupes, assigns team keys | `load/1` |
| src/bs_csv.erl | Minimal RFC 4180 CSV parser on UTF-8 binaries | `parse/1`, `read_file/1`, `read_maps/1` |
| src/bs_text.erl | Team-name normalisation, date/int parsing, accent folding | `normalize_team/1`, `split_team/1`, `parse_date/1`, `parse_int/1`, `fold/1`, `title/1`, `competition_name/2` |
| src/brazilian_soccer_mcp.app.src | OTP application resource file | — |
| test/bs_csv_tests.erl | CSV parser unit tests | 8 tests |
| test/bs_data_tests.erl | Dataset loading / dedupe tests | 12 tests |
| test/bs_text_tests.erl | Text/date/int helper tests | 31 tests |
| test/bs_query_tests.erl | Query-function tests | 14 tests |
| test/bs_tools_tests.erl | Tool dispatch/formatting tests | 7 tests |
| test/bs_mcp_tests.erl | JSON-RPC protocol tests | 10 tests |
| test/bs_integration_tests.erl | End-to-end tests over the real CSVs | 5 tests |
| test/bs_test_support.erl | Shared fixture loader for tests | (support, no tests) |

Build config: `rebar.config` (rebar3, EUnit, escript). No external dependencies (`rebar.lock` empty); uses OTP's built-in `json` module.
