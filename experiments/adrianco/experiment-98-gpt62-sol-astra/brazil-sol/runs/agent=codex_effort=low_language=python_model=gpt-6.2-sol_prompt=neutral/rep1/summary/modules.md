# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Loads the six Kaggle CSVs, normalizes team/competition names, merges overlapping fixtures, and answers all match/team/player/competition/stat queries | `Soccer`, `search_matches`, `team_stats`, `head_to_head`, `search_players`, `standings`, `team_rankings`, `tournament_bracket`, `match_statistics`, `club_profile`, `top_scorers`, `coverage` |
| server.py | JSON-RPC 2.0 MCP server over stdio: handshake, `tools/list`, `tools/call`, schema generation from `Soccer` method signatures | `Server`, `main()`, `tool_schema()` |
| test_soccer.py | unittest suite: 25 data/query scenarios (`SoccerScenarios`) + 1 end-to-end MCP stdio handshake (`MCPScenarios`) | 27 `test_*` methods across 2 TestCase classes |

(Build artifacts under `__pycache__` were removed by the agent; `data/kaggle/` holds the six provided CSVs and is not source.)
