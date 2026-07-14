# Summary: language=go_model=opus-4.8-fast_prompt=TDD · rep 1

- **Shape:** Go stdlib MCP server over stdio JSON-RPC, querying in-memory CSV datasets for Brazilian soccer matches and FIFA players
- **Structure:** 8 source modules, 5 test files (2,162 total lines of Go)
- **Interfaces:** 6 MCP tools (search_matches, team_record, head_to_head, standings, search_players, competition_stats)
- **Notable:** Zero external dependencies — pure Go stdlib; team name normalization handles accents, state suffixes, and parentheticals across 5 different CSV formats; standings avoids double-counting by picking best source per season

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
