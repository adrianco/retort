# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP server: JSON-RPC 2.0 over newline-delimited stdio; tool registry, dispatch, in-band error reporting | `main()`, `handle()`, `call_tool()`, `TOOLS` |
| soccer.py | Knowledge base: loads the 6 Kaggle CSVs, normalizes team names, answers all queries as formatted text | `KB`, `Match`, `normalize_team()`, `search_matches()`, `head_to_head()`, `team_record()`, `standings()`, `search_players()`, + 11 more query fns |
| test_soccer.py | pytest suite: normalization, data-load, 25 sample questions, MCP protocol, stdio e2e | 34 test functions (+18 parametrized normalize cases) |
