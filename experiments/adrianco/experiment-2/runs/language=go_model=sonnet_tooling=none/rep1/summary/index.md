# Summary: language=go_model=sonnet_tooling=none · rep 1

- **Shape:** Go stdlib MCP (JSON-RPC 2.0 over stdio) server for Brazilian soccer data, in-memory CSV store, no third-party deps.
- **Structure:** 5 source modules + 1 test file (`mcp_test.go`, 29 tests), ~1,514 source LOC.
- **Interfaces:** 6 MCP tools (search_matches, get_team_stats, search_players, get_standings, get_head_to_head, get_biggest_wins); 5 JSON-RPC methods handled.
- **Notable:** Pure standard library (zero deps); dual JSON-RPC framing (Content-Length + newline); all data held in memory with O(n) scans; no accent folding in name matching; tests depend on an external `data/kaggle/` dir not present in the archive.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
