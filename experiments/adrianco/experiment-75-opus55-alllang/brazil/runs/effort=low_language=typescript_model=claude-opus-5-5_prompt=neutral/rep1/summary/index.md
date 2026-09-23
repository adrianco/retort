# Summary: effort=low_language=typescript_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`, stdio) over an in-memory dataset loaded from 6 Kaggle CSVs, with a Zod-typed tool layer.
- **Structure:** 6 source modules + 1 Vitest test file (943 LOC total); clean separation of CSV parse → data model → query engine → text handlers → MCP transport.
- **Interfaces:** 14 MCP tools (no HTTP/CLI); ~30 exported query/format functions.
- **Notable:** Handles the spec's data-quality traps head-on — team-name normalization with state suffixes, multi-format date parsing, UTF-8 accents, and cross-file de-duplication so overlapping Série A sources aren't double-counted. Query layer is deliberately transport-agnostic so it is unit-testable without the MCP runtime.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
