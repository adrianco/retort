# Summary: language=rust model=opus-4.8-fast prompt=TDD · rep 1

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio) over an in-memory store loaded from Kaggle CSVs; `csv` + `serde_json`, no async runtime.
- **Structure:** 7 source modules (lib, main, model, normalize, data, query, mcp), tests colocated in every module (62 `#[test]` functions).
- **Interfaces:** 4 JSON-RPC methods, 8 MCP tools, ~15 exported `Database` query/stat methods.
- **Notable:** Two-tier team-name normalization (loose `normalize_team` for queries vs strict `canonical_id` for standings/dedup); `source_priority`-based per-season de-duplication across 5 overlapping match datasets; integration tests assert real-dataset facts (2019 Brasileirão = 380 matches, Flamengo champions on 90 pts).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
