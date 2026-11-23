# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/data.ex | CSV loading, team-name normalization (NFD fold + aliases + state-suffix stripping), multi-format date parsing, cross-source match de-duplication, FIFA player loading | `load/1`, `team/1`, `fold/1`, `date/1`, `rows/1` |
| lib/query.ex | Query engine: one generic match filter feeding matches/statistics/standings, plus players search and `team_profile` join; W/L/D records, points, goal aggregates, standings ranking, curated derby list | `run/3` (tools: team_profile, players, matches, statistics, standings) |
| lib/server.ex | MCP server: JSON-RPC 2.0 over stdio, tool schema definitions, `initialize`/`tools/list`/`tools/call` dispatch, argument validation | `main/1`, `process/2` |
| test/soccer_test.exs | ExUnit suite exercising loading, queries, stats, standings, players, MCP protocol | 9 test functions |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start()` |
| mix.exs | Project + escript build config | `Soccer.MixProject` |
