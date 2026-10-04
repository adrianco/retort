# Summary: effort=high · language=python · model=claude-opus-5-5 · prompt=neutral · rep 1

- **Shape:** Stdlib-only MCP (JSON-RPC 2.0 over stdio) server exposing 18 tools over six unified Kaggle CSV datasets of Brazilian soccer.
- **Structure:** 7 package modules + 2 top-level scripts, 7 test files (~57 test functions, ~113 cases).
- **Interfaces:** 18 MCP tools (no HTTP), internal `Match`/`Player`/`SoccerDB` schema; console entry point `brazilian-soccer-mcp`.
- **Notable:** No third-party runtime deps (hand-rolled CSV load, date/name normalisation, and JSON-RPC); cross-file dedup/merge so standings never double-count; two real end-to-end tests (stdio subprocess + official MCP SDK client); titles/standings computed from results, not hardcoded.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
