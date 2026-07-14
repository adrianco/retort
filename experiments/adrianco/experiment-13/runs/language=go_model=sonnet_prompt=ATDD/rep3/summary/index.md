# Summary: language=go_model=sonnet_prompt=ATDD · rep 3

- **Shape:** Go MCP server (mark3labs/mcp-go) over stdio with an in-memory CSV-backed query layer.
- **Structure:** 10 source modules (main + server + 2 data + 6 tools), 1 acceptance test file (10 tests); no unit-test files.
- **Interfaces:** 6 MCP tools (find_matches, get_team_stats, find_players, get_head_to_head, get_standings, get_statistics); no HTTP/CLI surface.
- **Notable:** Clean package split (data / server / tools); tests are black-box through the MCP protocol via `mcptest`, but run against the full real dataset rather than seeded fixtures, and there is no finer-grained unit TDD beneath the acceptance suite (an ATDD-prompt deviation). All queries are O(n) linear scans.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
