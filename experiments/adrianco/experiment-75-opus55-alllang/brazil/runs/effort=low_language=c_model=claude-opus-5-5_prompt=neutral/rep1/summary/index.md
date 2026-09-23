# Summary: effort=low_language=c_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Dependency-free C11 MCP server (JSON-RPC 2.0 over stdio) with a hand-written JSON parser over in-memory CSV data.
- **Structure:** 5 source modules + 1 test file (~1,495 lines total), libc-only.
- **Interfaces:** 12 MCP tools; no HTTP/CLI subcommands (stdio JSON-RPC transport).
- **Notable:** Exceeds the spec's 5 query categories with 12 tools; substantial team-name normalization (accent folding, alias table, state-suffix disambiguation) and cross-file match de-duplication. All 64 test assertions pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
