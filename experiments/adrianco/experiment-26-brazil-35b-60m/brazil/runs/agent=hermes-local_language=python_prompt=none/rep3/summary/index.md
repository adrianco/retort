# Summary: agent=hermes-local language=python prompt=none · rep 3

- **Shape:** Python MCP server (FastMCP, stdio) over pandas, querying 6 Kaggle CSVs of Brazilian soccer data.
- **Structure:** 4 source modules + 2 test files (121 tests, 23 classes).
- **Interfaces:** 0 HTTP routes / 11 MCP tools / 10 exported query functions.
- **Notable:** Clean 3-layer split (server → handlers → loader) with lazy per-CSV caching, team-name normalization, and multi-format date parsing. One latent bug: `find_matches` truncates with `.head(limit)` before sorting by date.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
