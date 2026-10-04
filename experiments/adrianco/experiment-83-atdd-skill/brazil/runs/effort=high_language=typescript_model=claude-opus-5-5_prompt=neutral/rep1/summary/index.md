# Summary: brazilian-soccer-mcp-server · rep 1

- **Shape:** TypeScript MCP server (@modelcontextprotocol/sdk, stdio) over an in-memory knowledge graph built from six Kaggle CSVs; zod-validated tools.
- **Structure:** 9 source modules, 7 test files (62 tests), 6 runtime/dev dependencies.
- **Interfaces:** 17 MCP tools (matches, teams, players, standings, cups, stats); no HTTP/CLI surface beyond the stdio entry point.
- **Notable:** One of the most complete approaches seen for this task — explicit duplicate-fixture merging, CBF tie-breaker standings, knockout-bracket winner inference, accent/date normalisation, and graceful handling of FIFA-19 licensing gaps. Large single-file query engine (`query.ts`, 774 lines) is the main structural cost.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
