# Summary: language=python_model=sonnet_prompt=ATDD · rep 2

- **Shape:** Python FastMCP server over pandas-loaded Kaggle CSVs — 6 query tools, no DB, in-memory frames.
- **Structure:** 2 source modules (`server.py`, `data_loader.py`) + 1 test file (`tests/test_acceptance.py`, 16 tests).
- **Interfaces:** 6 MCP tools (`find_matches`, `get_team_stats`, `find_players`, `get_standings`, `get_head_to_head`, `get_top_stats`); stdio transport.
- **Notable:** Clean separation of tool layer (formatting) from data layer (querying/aggregation). Tests are acceptance-only (driven through `mcp.call_tool`), with no finer-grained unit tests despite the ATDD prompt asking for unit TDD underneath.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
