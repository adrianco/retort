# Summary: effort=low_language=swift_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Swift Package Manager MCP server (JSON-RPC 2.0 over stdio) with a `SoccerKit` library and a thin executable; pure Foundation, no external dependencies.
- **Structure:** 8 source modules + 2 test files (812 source LOC, 315 test LOC); 34 test functions, 0 skips.
- **Interfaces:** 13 MCP tools + 4 JSON-RPC methods (initialize/ping/tools/list/tools/call); 6 CSVs → in-memory `[Match]` (5 sources) + 18,207 players.
- **Notable:** All standings/records/stats computed from match rows, not hardcoded; robust team-name normalization (accents, state suffixes, club aliases); custom RFC4180 CSV parser; dataset de-duplication for clean per-season standings. Tools go beyond spec (derbies, finals, team_profile, biggest_wins, nationality_clubs).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
