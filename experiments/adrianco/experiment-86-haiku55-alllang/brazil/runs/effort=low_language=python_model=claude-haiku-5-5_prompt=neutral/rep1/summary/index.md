# Summary: effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Python stdlib-only MCP server (hand-rolled JSON-RPC 2.0 over stdio) over an in-memory soccer knowledge base built from six Kaggle CSVs.
- **Structure:** 6 source modules, 5 test files (44 test functions; `test_real_dataset` adds 24 parametrized sample-question cases).
- **Interfaces:** 4 JSON-RPC methods, 11 MCP tools, 1 CLI entrypoint; no HTTP routes.
- **Notable:** No third-party dependencies — MCP protocol implemented by hand rather than via the `mcp` SDK. Careful team-name normalization (state suffixes, accents, aliases) and per-(competition, season) de-duplication across overlapping files. Tests run against both a hand-checked fixture and the real datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
