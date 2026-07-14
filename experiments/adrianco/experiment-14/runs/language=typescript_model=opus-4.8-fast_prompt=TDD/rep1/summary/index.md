# Summary: language=typescript_model=opus-4.8-fast_prompt=TDD · rep 1

- **Shape:** TypeScript MCP server (@modelcontextprotocol/sdk, stdio) over an in-memory CSV-backed query engine, with Zod-validated tool inputs.
- **Structure:** 8 source modules, 7 test files (89 tests).
- **Interfaces:** 8 MCP tools / 0 CLI subcommands / `SoccerDatabase` with 8 query methods.
- **Notable:** Clean layered design (loader → database → tools → format) deliberately split so each layer is unit-testable; thorough accent/suffix team-name normalization with an alias table and ambiguous-base handling; cross-dataset canonicalization to avoid double-counting overlapping (competition, season) groups. Consistent with the TDD prompt — module-by-module unit coverage plus a real-data integration suite.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
