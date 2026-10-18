# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer_mcp.erl | MCP server over stdio (JSON-RPC 2.0, one msg/line); handles initialize/ping/tools/list/tools/call | `main/1`, `handle/2` |
| src/soccer_tools.erl | MCP tool surface: 8 tool definitions + dispatch + text formatting | `definitions/0`, `call/3` |
| src/soccer_stats.erl | Pure query functions over loaded matches/players (search, record, standings, summaries) | `search/2`, `record/2`, `standings/3`, `league_summary/3`, `biggest_wins/3`, `search_players/2`, `club_summary/2` |
| src/soccer_loader.erl | Reads the 6 Kaggle CSVs into one normalized match list + player list; dedupes; marks cup finals | `load/1` |
| src/soccer_csv.erl | Minimal RFC 4180 CSV parser (BOM, CRLF, quoted/multiline fields) | `parse/1`, `parse_maps/1` |
| src/soccer_teams.erl | Resolves club-name variants to a canonical display name + match tokens | `resolve/1` |
| src/soccer_util.erl | Text helpers: team-name normalization, accent-folding tokenizer, date/number parsing | `team_name/1`, `tokens/1`, `parse_date/1`, `format_date/1`, `parse_number/1`, `trim/1` |
| src/soccer_mcp.app.src | OTP application resource file | (app metadata) |
| test/soccer_csv_tests.erl | CSV parser edge cases | 4 test functions |
| test/soccer_data_tests.erl | Loader integration over real data (sources, Fla-Flu, cup finals, Brazilian players) | 4 generator tests |
| test/soccer_mcp_tests.erl | MCP protocol: initialize, notifications, tools/list, tools/call, errors | 6 test functions |
| test/soccer_stats_tests.erl | Query functions over fixture matches/players | 8 test functions |
| test/soccer_util_tests.erl | Name/date/number helpers | 6 test functions |
