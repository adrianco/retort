# Summary: language=go_model=claude-opus-4-8-fast · rep 3

- **Shape:** Go stdlib-only MCP stdio server over an in-memory knowledge graph built from 6 embedded Kaggle CSVs.
- **Structure:** 10 source modules (+ 2 test files) across `main`, `internal/mcp`, `internal/soccer`; ~2,880 LOC of Go.
- **Interfaces:** 7 MCP tools, 5 JSON-RPC methods, 2 CLI flags; no HTTP routes (stdio transport).
- **Notable:** Zero third-party dependencies — both the MCP protocol and CSV ingestion are hand-rolled on the standard library. Careful data-quality handling: per-(competition, season) authoritative-source selection to avoid double-counting, accent/suffix-insensitive team-name matching, multi-format date and float-goal parsing.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
