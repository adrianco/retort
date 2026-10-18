# Summary: effort=low_language=java_model=claude-haiku-5-5_prompt=neutral · rep 1

- **Shape:** Pure-Java MCP server (JSON-RPC 2.0 over stdio, Jackson only) with an in-memory query engine over six Kaggle CSVs.
- **Structure:** 12 main modules + 6 test files (56 tests).
- **Interfaces:** 4 JSON-RPC methods / 7 MCP tools / ~10 Dataset query functions.
- **Notable:** No MCP SDK dependency — hand-rolled JSON-RPC on Jackson; thorough team-name normalization (state suffixes, aliases, accent folding) and multi-format date parsing; cup finals inferred from last round per season. BDD-style tests run against the real datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
