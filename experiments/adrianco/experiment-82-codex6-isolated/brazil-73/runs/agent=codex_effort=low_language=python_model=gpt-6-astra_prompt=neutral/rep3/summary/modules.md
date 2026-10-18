# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Offline knowledge-graph + query engine over the six CSVs | `SoccerGraph`, `team_key()`, `competition_key()`, `date_key()`, `number()`, `page()` |
| server.py | Dependency-free JSON-RPC 2.0 / MCP stdio server | `MCPServer`, `tool_definitions()`, `main()` |
| test_soccer.py | Given/When/Then unittest suite over real CSVs | `SoccerScenarios` (12 test methods) |
| README.md | Usage, tool catalogue, data notes | n/a (docs) |

`data/kaggle/` holds the six provided CSVs (not source). Build artifacts (`.coverage`,
`.idiomatic_cache.json`, `_agent_*.log`) are excluded.
