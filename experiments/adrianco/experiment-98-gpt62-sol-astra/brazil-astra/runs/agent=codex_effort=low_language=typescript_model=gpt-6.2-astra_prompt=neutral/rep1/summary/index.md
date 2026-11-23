# Summary: agent=codex effort=low language=typescript model=gpt-6.2-astra prompt=neutral · rep 1

- **Shape:** TypeScript MCP server (hand-rolled JSON-RPC 2.0 over stdio) over an in-memory knowledge graph built from six Kaggle CSVs.
- **Structure:** 3 source modules (data/queries/server) + 1 test module, no runtime dependencies (only typescript + @types/node).
- **Interfaces:** 4 MCP tools (matches, records, statistics, players); 5 JSON-RPC methods; one unified `query()` engine.
- **Notable:** very compact/golfed style (single-letter vars, nested ternaries); cross-source fixture dedup so the 2019 league table counts each match once; 27 tests all pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
