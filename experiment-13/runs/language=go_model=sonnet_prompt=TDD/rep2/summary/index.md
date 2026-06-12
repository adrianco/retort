# Summary: language=go_model=sonnet_prompt=TDD · rep 2

- **Shape:** Go MCP server (mark3labs/mcp-go) over stdio, in-memory CSV-backed query layer for Brazilian soccer data.
- **Structure:** 8 source modules, 5 test files (33 test functions, 0 skipped).
- **Interfaces:** 6 MCP tools (search_matches, head_to_head, team_stats, standings, search_players, get_statistics); no HTTP/CLI.
- **Notable:** Clean separation of loader / normalizer / query / tool layers; all 6 datasets loaded; standings and stats computed from match data. Team-name normalization strips state suffixes but not accents.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
