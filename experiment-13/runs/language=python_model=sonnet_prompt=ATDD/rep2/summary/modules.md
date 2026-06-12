# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | FastMCP server; defines and registers the soccer query tools | `mcp`, `find_matches`, `get_team_stats`, `find_players`, `get_standings`, `get_head_to_head`, `get_top_stats` |
| data_loader.py | Loads + normalizes the Kaggle CSVs, builds a unified match table, and computes all aggregates | `DataStore`, `normalize_team_name`, `canonical_competition` |
| tests/test_acceptance.py | End-to-end acceptance tests driving the server only through `mcp.call_tool` | 16 test functions (AC-1 … AC-15 + perf) |
