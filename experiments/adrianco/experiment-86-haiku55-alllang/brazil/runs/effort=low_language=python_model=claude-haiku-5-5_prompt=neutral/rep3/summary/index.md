# Summary: effort=low language=python model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Pure-stdlib Python MCP server (hand-rolled JSON-RPC 2.0 over stdio) over an in-memory query layer loaded from six Kaggle CSVs.
- **Structure:** 7 source modules + 4 test files (54 test functions), 1309 source LOC / 445 test LOC.
- **Interfaces:** 8 MCP tools, 4 MCP protocol methods, 1 CLI entry point; no third-party runtime deps (only pytest for dev).
- **Notable:** Thorough team-name normalization (accents, state suffixes, legal-name aliases, state-based disambiguation of Atlético-MG vs Athletico-PR) and cross-source match de-duplication; answers formatted to mirror the TASK.md example outputs.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
