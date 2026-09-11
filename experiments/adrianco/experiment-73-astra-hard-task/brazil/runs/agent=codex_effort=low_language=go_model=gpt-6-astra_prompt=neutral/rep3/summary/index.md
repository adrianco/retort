# Summary: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 3

- **Shape:** Go stdlib MCP stdio server (JSON-RPC 2.0) over in-memory Brazilian-soccer datasets — no third-party dependencies.
- **Structure:** 3 source modules (main/data/query) + 1 test file; ~1165 source LOC, 365 test LOC.
- **Interfaces:** 9 MCP tools (matches, team stats, head-to-head, standings, statistics, competition results, player search, team graph, dataset info); no HTTP, one `-data` CLI flag.
- **Notable:** Serious data-engineering for a low-effort run — cross-source fixture dedup with provenance retention, team-name normalization/aliasing, cup-stage inference, a typed knowledge-graph tool, and strict MCP handshake + unknown-field rejection at the boundary.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
