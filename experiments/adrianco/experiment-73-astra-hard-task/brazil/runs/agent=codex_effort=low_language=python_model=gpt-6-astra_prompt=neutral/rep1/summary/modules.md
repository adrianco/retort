# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Offline knowledge graph: loads six CSVs, deduplicates matches across sources, normalizes team names, and answers all queries | `SoccerGraph`, `team_key()`, `parse_date()`, `competition_name()`, `page()` |
| server.py | Dependency-free MCP stdio JSON-RPC server; auto-derives tool schemas from `SoccerGraph` method signatures | `MCPServer`, `TOOLS`, `tool_definition()`, `validate_arguments()`, `main()` |
| build.py | Packages `soccer.py` + `server.py` into a stdlib-only zipapp | `build()` |
| test_soccer.py | Behavior tests over hand-built fixtures and the full dataset, plus MCP-protocol and stdio-subprocess tests | 20 test methods across `FixtureTests`, `DatasetTests`, `ProtocolTests` |
| sample_questions.json | 28 canned (question, tool, arguments) examples exercised by `test_sample_questions` | data file |
| pyproject.toml | Packaging metadata; `dependencies = []` (stdlib only) | `brazilian-soccer-mcp` console script |
