# Summary: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 3

- **Shape:** Offline Brazilian-soccer knowledge graph + hand-rolled MCP JSON-RPC stdio server (stdlib only: `csv`, `unicodedata`, `argparse`, `json`).
- **Structure:** 2 source modules + 1 test module (485 LOC total), no third-party dependencies.
- **Interfaces:** 5 MCP methods, 13 read-only tools, backed by in-memory match/player graph loaded from 6 CSVs.
- **Notable:** Cross-source match deduplication with ±1-day reconciliation; honest capability limits (`top_scorers` and knockout `standings` refuse rather than fabricate); regression test pins Flamengo 2019 (38 matches, 90 pts) against real data.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
