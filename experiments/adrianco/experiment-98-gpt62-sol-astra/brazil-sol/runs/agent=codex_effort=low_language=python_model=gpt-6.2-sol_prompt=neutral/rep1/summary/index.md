# Summary: brazil-sol · agent=codex effort=low model=gpt-6.2-sol prompt=neutral · rep 1

- **Shape:** Pure-stdlib Python MCP server (JSON-RPC 2.0 over stdio) over an in-memory soccer knowledge graph built from six Kaggle CSVs.
- **Structure:** 3 modules (soccer, server, test_soccer), 1 test file, 919 LOC, zero third-party dependencies.
- **Interfaces:** 11 MCP tools / 5 JSON-RPC methods / 12 exported `Soccer` methods; no HTTP, no CLI.
- **Notable:** Unusually thorough fixture-merge/dedup across five match CSVs, a team-name alias+state-disambiguation table, multi-protocol-version negotiation, and a full end-to-end stdio handshake test — well beyond a minimal pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
