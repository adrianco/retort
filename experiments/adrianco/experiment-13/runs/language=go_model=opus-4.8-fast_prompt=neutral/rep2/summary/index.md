# Summary: language=go_model=opus-4.8-fast_prompt=neutral · rep 2

- **Shape:** Go MCP server (JSON-RPC 2.0 over stdio, zero external deps) with an in-memory CSV-backed soccer knowledge base.
- **Structure:** 10 source modules across 3 packages (mcp, server, soccer) + 4 test files.
- **Interfaces:** 8 MCP tools / 5 JSON-RPC methods / ~8 exported query functions; 1 CLI flag.
- **Notable:** Pure stdlib (no go.sum); careful data-engineering layer — cross-dataset dedup, per-(competition,season) source selection, accent/state-suffix team-name normalization. Integration test validates the headline 2019 Brasileirão table (Flamengo, 90 pts) against the real shipped data.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
