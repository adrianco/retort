# Summary: language=typescript_model=sonnet_prompt=neutral · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk` over stdio) with an in-memory CSV-backed query engine for Brazilian soccer data.
- **Structure:** 3 source modules + 1 test file (46 tests), ~1,118 source LOC.
- **Interfaces:** 9 MCP tools (matches, team stats, head-to-head, standings, player search, aggregate stats); no HTTP/CLI surface.
- **Notable:** Clean separation of loader / query-engine / server. Overlapping source datasets (Brasileirão 2012–2022 vs historical 2003–2019) are unioned without cross-source dedup, so standings and per-team/aggregate stats double-count for 2012–2019.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
