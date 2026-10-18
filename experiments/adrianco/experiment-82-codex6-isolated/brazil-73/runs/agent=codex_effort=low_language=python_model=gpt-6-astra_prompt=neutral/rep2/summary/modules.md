# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Offline knowledge graph: loads 6 CSVs, normalizes teams, dedups fixtures, answers match/team/player/competition/stats queries (stdlib only) | `SoccerGraph`, `normalize_team()`, `team_key()`, `parse_date()`, `page()` |
| server.py | Newline-delimited JSON-RPC 2.0 MCP stdio server; reflects `SoccerGraph` methods into tool schemas | `MCPServer`, `SCHEMAS`, `tool_schema()`, `validate()`, `main()` |
| test_soccer.py | Given/When/Then unittest suite (20 tests across data, synthetic, and protocol scenarios) | `DataScenarios`, `SyntheticScenarios`, `ProtocolScenarios` |
| sample_questions.json | 26 natural-language questions mapped to tool + arguments (used by a test) | — |
| README.md | Usage, architecture, tool reference | — |
