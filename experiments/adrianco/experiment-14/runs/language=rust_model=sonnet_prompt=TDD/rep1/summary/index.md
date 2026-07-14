# Summary: language=rust_model=sonnet_prompt=TDD · rep 1

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio) over in-memory Brazilian-soccer datasets loaded from CSV; serde/serde_json/csv/anyhow/tokio.
- **Structure:** 6 source modules (lib, models, data, query, mcp, main), tests co-located in 4 modules (54 `#[test]` functions, no skips).
- **Interfaces:** 6 MCP tools (search_matches, head_to_head, team_stats, competition_standings, search_players, statistics) + the `query::*` library API.
- **Notable:** Clean module separation and thorough test-first coverage consistent with the TDD prompt. All 6 datasets loaded with per-file column mapping. Minor rough edges: lexicographic date-range comparison (wrong for non-ISO dates), substring team matching, unused `tokio` async runtime.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
