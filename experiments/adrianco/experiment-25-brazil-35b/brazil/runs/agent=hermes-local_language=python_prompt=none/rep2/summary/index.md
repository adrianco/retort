# Summary: agent=hermes-local language=python prompt=none · rep 2

- **Shape:** Python MCP server (FastMCP) over pandas; 6 Kaggle CSVs loaded into a unified match DataFrame + FIFA player frame, queried by a single `QueryEngine`.
- **Structure:** 4 source modules + 1 test file (88 tests, 10 classes).
- **Interfaces:** 22 MCP tools / 0 HTTP routes / `QueryEngine` with ~20 public query methods.
- **Notable:** Thorough coverage of all 5 capability categories; row-wise (`iterrows`) aggregation rather than vectorized pandas; overlapping Brasileirão datasets share one competition label so standings can double-count; `find_copa_do_brasil_final` uses `contains("copa")` which also matches Libertadores.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
