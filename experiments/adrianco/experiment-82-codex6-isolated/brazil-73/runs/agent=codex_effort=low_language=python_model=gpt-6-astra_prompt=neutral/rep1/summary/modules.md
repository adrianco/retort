# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer.py | Loads the six Kaggle CSVs into an in-memory knowledge graph; normalization, query and aggregation logic | `SoccerGraph`, `team_name()`, `competition_name()`, `date_value()`, `fold()`, `FILES`, `DATA` |
| server.py | Hand-rolled MCP stdio JSON-RPC server exposing the graph's methods as 11 MCP tools | `MCPServer`, `validate()`, `SCHEMAS`, `main()` |
| test_soccer.py | unittest suite: graph query contracts + MCP protocol scenarios | `SoccerScenarios` (13 tests), `ProtocolScenarios` (2 tests) |
| sample_questions.json | 27 tool-call scenarios exercised by `test_twenty_five_sample_questions` | data file |
| data/kaggle/*.csv | Provided match + FIFA player datasets (6 files) | data source |
