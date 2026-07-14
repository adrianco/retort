# Summary: language=python_model=sonnet_prompt=TDD · rep 2

- **Shape:** FastMCP (stdio) server over pandas, with a clean 3-layer split: DataLoader → QueryEngine → MCP tools.
- **Structure:** 3 source modules, 3 test files (45 test functions total).
- **Interfaces:** 0 HTTP routes / 7 MCP tools / 7 exported `QueryEngine` methods + 4 loader/helper functions.
- **Notable:** TDD-style "Cycle 1–9" sectioning mirrored between tests and implementation; query-engine tests run against in-memory fixture DataFrames (no CSV I/O), so they are fast and isolated. Aggregation uses `iterrows()` rather than vectorized pandas.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
