# Summary: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 2

- **Shape:** Go stdlib MCP server (JSON-RPC 2.0 over stdio) over an in-memory soccer knowledge graph loaded from six Kaggle CSVs.
- **Structure:** 3 source modules (main/data/query) + 1 test file (7 test functions), zero external dependencies.
- **Interfaces:** MCP protocol (initialize/ping/tools/list/tools/call) exposing 7 read-only query tools; `-data` CLI flag.
- **Notable:** Cross-source match **deduplication with provenance tracking and score-conflict reconciliation**; team-name normalization via accent-folding + state-suffix stripping + alias table; validated against real datasets (18,207 players, 2019 Brasileirão reconstructed to the known 380-game/90-pt-Flamengo table). Code is extremely dense (long single-statement conditionals), which shows in the low idiomatic score.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
