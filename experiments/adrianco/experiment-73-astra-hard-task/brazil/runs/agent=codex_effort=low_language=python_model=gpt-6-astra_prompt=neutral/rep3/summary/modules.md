# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Offline knowledge-graph + query engine over the Kaggle CSVs (loading, team/date/competition normalization, dedup across sources, all query methods) | `SoccerGraph`, `team_name()`, `competition_name()`, `date_value()`, `number()`, `fold()` |
| server.py | Read-only MCP JSON-RPC stdio server exposing the graph's methods as tools | `MCPServer`, `TOOLS`, `main()` |
| test_soccer.py | `unittest` suite exercising loading, normalization, filters, arithmetic, players, 23 sample questions, and the protocol/stdio server | 9 `test_*` methods, `EXAMPLES` |
| README.md | Usage/architecture notes | — |
