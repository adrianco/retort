# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer_mcp.erl | JSON-RPC MCP server over stdio: initialize / tools/list / tools/call, dispatch to query fns | `main/0`, `handle/2`, `tools/0` |
| src/soccer_data.erl | Load 5 match CSVs + FIFA players, normalize into match/player maps | `load/0`, `load/1`, `matches/1`, `players/1`, `normalize_team/1`, `parse_date/1` |
| src/soccer_csv.erl | Minimal CSV reader + RFC-ish quoted-field line parser | `read/1`, `parse_line/1` |
| src/soccer_query.erl | Query layer: match search, team stats, head-to-head, standings, player search, aggregates, NL `ask` | `find_matches/2`, `team_stats/2`, `head_to_head/3`, `standings/3`, `search_players/2`, `aggregate/2`, `answer/2` |
| src/soccer_json.erl | Dependency-free JSON encode/decode | `encode/1`, `decode/1` |
| src/brazilian_soccer_mcp_app.erl | OTP application behaviour stub | `start/2`, `stop/1` |
| src/brazilian_soccer_mcp.app.src | OTP application resource file | — |
| src/soccer_tests.erl | EUnit suite over in-memory sample data | 5 test functions |

No external dependencies (`rebar.lock` empty); `kernel` + `stdlib` only.
