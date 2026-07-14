# Summary: language=clojure model=opus-4.8-fast prompt=neutral · rep 1

- **Shape:** Clojure MCP server (JSON-RPC 2.0 over stdio, dependency-light) over an in-memory knowledge graph built from the bundled Kaggle CSVs.
- **Structure:** 6 source modules, 3 test files (26 deftests, ~101 `is` assertions); ~1037 LoC src / ~282 LoC test.
- **Interfaces:** 4 MCP/JSON-RPC methods + 10 MCP tools; no HTTP/REST surface (stdio transport per the MCP spec).
- **Notable:** Clean layering — pure `query`/`normalize`/`format` cores with the protocol plumbing isolated and unit-testable without a process. Robust team-name normalization (accent/suffix/alias/substring) and cross-source dedup directly address the spec's data-quality notes. Tests mix a hand-verified synthetic graph with real-dataset coverage (incl. reproducing the 2019 Brasileirão table: Flamengo, 90 pts).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
