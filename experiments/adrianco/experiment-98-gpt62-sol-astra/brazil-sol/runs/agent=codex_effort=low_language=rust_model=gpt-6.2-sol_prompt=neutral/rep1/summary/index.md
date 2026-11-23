# Summary: agent=codex_effort=low_language=rust_model=gpt-6.2-sol_prompt=neutral · rep 1

- **Shape:** Rust MCP (JSON-RPC 2.0 over stdio) server over an in-memory soccer knowledge graph loaded from 6 Kaggle CSVs; only `csv` + `serde` deps.
- **Structure:** 4 source modules + 1 test file (10 tests), ~1259 source LOC.
- **Interfaces:** 4 MCP methods + 7 query tools (`search_matches`, `team_stats`, `search_players`, `standings`, `cup_bracket`, `analyze_matches`, `dataset_info`).
- **Notable:** Unusually complete for a low-effort run — team-name normalization with an alias table, multi-format date parsing, cross-feed fixture de-duplication/merge, computed standings with relegation + double-round-robin guard, derby detection, and a real end-to-end stdio handshake test. All tests pass (test_coverage=1.0).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
