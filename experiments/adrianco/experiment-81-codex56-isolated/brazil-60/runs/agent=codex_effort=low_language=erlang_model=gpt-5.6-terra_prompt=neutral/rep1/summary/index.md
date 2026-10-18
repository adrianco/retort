# Summary: agent=codex effort=low language=erlang model=gpt-5.6-terra prompt=neutral · rep 1

- **Shape:** Dependency-free Erlang MCP server (JSON-RPC 2.0 over stdio) with its own CSV and JSON parsers; in-memory query layer over six Kaggle soccer CSVs.
- **Structure:** 6 source modules + 1 `.app.src` + 1 EUnit test module; ~202 lines of Erlang total.
- **Interfaces:** 7 MCP tools (search_matches, team_stats, head_to_head, standings, search_players, aggregate_stats, ask); no HTTP, no external deps (`kernel`/`stdlib` only).
- **Notable:** Extremely terse style — multiple statements packed per line in `soccer_mcp`/`soccer_query`/`soccer_json` (low idiomatic score, 0.2). Hand-rolled JSON + CSV instead of libraries. Entry module is `soccer_mcp`, not `brazilian_soccer_mcp`, which the harness runtime/factual probe could not locate.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
