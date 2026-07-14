# Summary: language=rust · model=sonnet-5 · prompt=none · rep 1

- **Shape:** Rust MCP server (official `rmcp` SDK over stdio) over an in-memory store of six Kaggle CSVs, exposing 12 query tools for Brazilian soccer matches/teams/standings/players.
- **Structure:** 8 source modules (`main`, `lib`, `model`, `normalize`, `data`, `store`, `queries`, `server`) + 1 integration test file; 32 tests total (27 integration + 5 unit).
- **Interfaces:** 12 MCP tools; no HTTP routes; 1 optional CLI positional arg (data dir).
- **Notable:** Clean layered architecture (data → store → queries → server). Handles two genuine data-quality hazards explicitly: the 2012–2019 Brasileirão dataset overlap (deduplicated at load) and same-base club names across states (e.g. Atlético-MG vs Atlético-GO) via a data-driven identity layer, both covered by regression tests. Rust `"x".contains("")`-always-true pitfall guarded in team/club matching.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
