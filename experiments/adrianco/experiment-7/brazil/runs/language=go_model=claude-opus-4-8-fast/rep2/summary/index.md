# Summary: language=go_model=claude-opus-4-8-fast · rep 2

- **Shape:** Go stdio MCP server (hand-rolled JSON-RPC 2.0, zero external deps) over an in-memory CSV-backed query engine for Brazilian soccer data.
- **Structure:** 7 source modules, 4 test files (25 test functions, ~1886 source LOC / ~610 test LOC).
- **Interfaces:** 7 MCP tools (find_matches, team_stats, head_to_head, search_players, standings, competition_stats, list_competitions); JSON-RPC methods initialize/ping/tools.list/tools.call.
- **Notable:** Implements the MCP protocol from scratch rather than using an SDK; careful team-name normalization (accent folding, state suffixes), cross-dataset de-duplication, and single-source standings to avoid double-counting overlapping Brasileirão datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
