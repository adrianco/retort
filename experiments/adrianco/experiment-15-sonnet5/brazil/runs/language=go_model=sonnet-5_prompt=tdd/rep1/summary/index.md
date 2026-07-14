# Summary: language=go · model=sonnet-5 · prompt=tdd · rep1

- **Shape:** Go MCP server (official `modelcontextprotocol/go-sdk`, stdio transport) over an in-memory `soccer.Store` loaded from six Kaggle CSVs.
- **Structure:** 10 source modules across `cmd/server`, `internal/mcpserver`, `internal/soccer`; 8 test files (40 test functions).
- **Interfaces:** 0 HTTP routes / 7 MCP tools / 1 CLI flag (`-data-dir`); library API of ~7 `Store` query methods plus `NormalizeTeamKey`/`ParseDate` helpers.
- **Notable:** Clean layered separation (loaders → store queries → formatters → MCP tools); dedicated team-name normalization (accent stripping, state-suffix removal, aliases) and multi-format date parsing; all queries are linear scans over in-memory slices; overlapping Brasileirão sources deliberately kept as distinct competitions rather than deduplicated.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
