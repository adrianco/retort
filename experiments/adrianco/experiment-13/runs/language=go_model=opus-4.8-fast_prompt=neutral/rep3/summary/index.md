# Summary: language=go_model=opus-4.8-fast_prompt=neutral · rep 3

- **Shape:** Go MCP server (JSON-RPC 2.0 over stdio, stdlib-only) over an in-memory soccer knowledge graph built from 6 Kaggle CSVs.
- **Structure:** 9 source modules (2 packages: `mcp`, `soccer`) + 4 test files (~1,944 LOC source / ~568 LOC tests).
- **Interfaces:** 5 JSON-RPC methods + 7 MCP tools; reusable `soccer` query-engine API. No HTTP, no external network calls.
- **Notable:** Zero third-party dependencies (no go.sum). Strong data-engineering: multi-format date/goal parsing, accent folding without `golang.org/x/text`, region-aware team disambiguation, and per-(competition,season) source deduplication.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
