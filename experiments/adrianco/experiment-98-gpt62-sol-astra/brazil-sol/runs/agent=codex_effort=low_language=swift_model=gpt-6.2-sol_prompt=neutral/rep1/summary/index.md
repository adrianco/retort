# Summary: agent=codex effort=low language=swift model=gpt-6.2-sol prompt=neutral · rep 1

- **Shape:** Swift Package (SPM) MCP server — JSON-RPC 2.0 over stdio, pure Foundation, zero external dependencies, hand-rolled CSV parser and in-memory graph.
- **Structure:** 6 library modules + 1 executable + 1 test file (7 XCTest methods), ~1200 source LOC + ~254 test LOC.
- **Interfaces:** 6 MCP tools, 4 JSON-RPC methods, 1 CLI (`--data-dir`/`--help`); all 6 datasets in `data/kaggle/` loaded and queryable.
- **Notable:** Unusually complete for `effort=low` — cross-source fixture merging, name/alias normalization, cup-bracket stage inference, double-round-robin completeness checks, and pagination. Carries a cluster of dataset-specific hard-coded corrections in `Graph.swift` (lowers maintainability) and tests assert exact dataset counts/results, pinning the implementation tightly to this data snapshot.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
