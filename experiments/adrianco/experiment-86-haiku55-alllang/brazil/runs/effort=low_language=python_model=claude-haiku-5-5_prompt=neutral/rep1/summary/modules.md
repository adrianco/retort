# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `brazilian_soccer_mcp/server.py` | Hand-rolled MCP server over stdio (JSON-RPC 2.0); registers 11 soccer tools | `main()`, `serve()`, `handle_message()`, `SoccerTools` |
| `brazilian_soccer_mcp/queries.py` | In-memory knowledge base answering match/team/player/standings/stats queries | `SoccerKnowledgeBase`, `TeamRecord`, `HeadToHead`, `StandingRow`, `SeasonStats` |
| `brazilian_soccer_mcp/data.py` | CSV loaders merging the six Kaggle datasets into `Match`/`Player` records | `load_matches()`, `load_players()`, `parse_date()`, `Match`, `Player`, `Team` |
| `brazilian_soccer_mcp/names.py` | Team/competition name normalization (state suffixes, accents, aliases) | `parse_team()`, `fold()`, `display_name()`, `resolve_competition()` |
| `brazilian_soccer_mcp/formatting.py` | Renders query results into human-readable text for tool responses | `format_matches()`, `format_record()`, `format_standings()`, `format_players()`, … |
| `brazilian_soccer_mcp/__init__.py` | Package marker | (none) |
| `tests/conftest.py` | Pytest fixtures: small hand-checked sample dataset + real-data KB | `sample_kb`, `real_kb`, `write_sample_dataset()` |
| `tests/test_match_queries.py` | Match/team/head-to-head/standings/stats behaviour tests | 19 test functions |
| `tests/test_mcp_server.py` | JSON-RPC protocol tests (initialize, tools/list, tools/call) | 9 test functions |
| `tests/test_player_queries.py` | Player search/filter/club-profile tests | 7 test functions |
| `tests/test_names.py` | Name-normalization unit tests | 3 test functions |
| `tests/test_real_dataset.py` | Acceptance tests against the real Kaggle files + 24 sample questions | 6 test functions (24 parametrized) |
