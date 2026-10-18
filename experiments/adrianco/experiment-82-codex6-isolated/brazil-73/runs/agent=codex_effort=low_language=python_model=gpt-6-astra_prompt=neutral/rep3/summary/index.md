# Summary: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 3

- **Shape:** Dependency-free Python MCP (JSON-RPC 2.0 stdio) server over an offline, in-memory soccer knowledge graph built from the six provided CSVs.
- **Structure:** 2 source modules (`soccer.py` engine, `server.py` protocol) + 1 test module (12 methods, 24-question routing subtest), README, stdlib-only.
- **Interfaces:** 9 MCP tools; JSON-RPC `initialize`/`ping`/`tools/list`/`tools/call`.
- **Notable:** Goes well beyond the spec — cross-source fixture dedup with provenance, graph traversal (`graph_neighbors`), a `coverage` tool listing data limitations, curated derby detection, and careful refusal to certify champions/relegations from partial data. Hand-rolled MCP protocol (no SDK) kept it zero-dependency.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
