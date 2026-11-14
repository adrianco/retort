# Summary: effort=low language=elixir model=claude-fable-5-2 prompt=neutral · rep 1

- **Shape:** Elixir MCP server (JSON-RPC 2.0 over stdio, zero external deps) querying six Kaggle CSVs loaded into an in-memory knowledge base cached in `:persistent_term`.
- **Structure:** 11 source modules (`lib/`), 4 test files (46 tests, no skips).
- **Interfaces:** 1 MCP transport (stdio) exposing 16 MCP tools; escript + `mix soccer.mcp` entry points. No HTTP routes.
- **Notable:** Pure `handle/1` protocol core (testable without a transport); custom RFC-4180 CSV parser and accent-insensitive team-name canonicalisation; same fixture merged across source files to avoid double counting. Uses Elixir 1.18's built-in `JSON` module so `deps: []`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
