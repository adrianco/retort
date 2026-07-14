# Summary: language=elixir model=opus-4.8-fast prompt=ATDD · rep 1

- **Shape:** Elixir/OTP MCP server (JSON-RPC 2.0 over stdio) over six in-memory Kaggle CSV datasets for Brazilian soccer.
- **Structure:** 16 lib modules + 1 test support module, 6 acceptance test files (30 tests).
- **Interfaces:** 5 JSON-RPC methods, 8 MCP tools, 1 escript CLI; no HTTP routes.
- **Notable:** Data loaded once into `:persistent_term` for lock-free reads; careful CSV de-duplication and single-authoritative-source selection per season so standings/stats aren't double-counted; thorough name normalisation (state-suffix stripping, accent folding) and multi-format date parsing. Tests are pure acceptance tests driving the system only through the MCP protocol boundary (no internal back-doors), matching the ATDD prompt.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
