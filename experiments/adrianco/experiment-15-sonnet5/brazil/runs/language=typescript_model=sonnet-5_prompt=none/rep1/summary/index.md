# Summary: language=typescript · model=sonnet-5 · prompt=none · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`, stdio) over 6 in-memory CSV datasets, with `zod`-validated tools.
- **Structure:** 12 source modules (entry + server + loader + normalize + types + 6 query modules + shared helpers), 7 test files (49 tests).
- **Interfaces:** 12 MCP tools (matches, head-to-head, team record, standings, stats, FIFA players); no HTTP/CLI surface.
- **Notable:** Clean layered separation (loader → query modules → server); deliberate cross-dataset dedup and team-name normalization for accent/state-suffix variants; standings computed from raw match results rather than hardcoded.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
