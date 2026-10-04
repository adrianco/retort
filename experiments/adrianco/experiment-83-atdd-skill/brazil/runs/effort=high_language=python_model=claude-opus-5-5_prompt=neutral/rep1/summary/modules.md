# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brsoccer/__init__.py | Package marker + `__version__` | `__version__` |
| brsoccer/__main__.py | `python -m brsoccer` entry → `server.main()` | `main` |
| brsoccer/data.py | Load/unify the six Kaggle CSVs into `Match`/`Player`; name & date normalisation; dedup/merge | `SoccerDB`, `get_db()`, `Match`, `Player`, `parse_date()`, `COMPETITIONS` |
| brsoccer/teams.py | Team-name normalisation, aliasing, fuzzy resolution | `Team`, `normalize_team()`, `fold()` |
| brsoccer/queries.py | Query layer — one function per question family; returns `{text, data}` | `search_matches`, `head_to_head`, `team_record`, `team_profile`, `standings`, `knockout_bracket`, `finals`, `team_rankings`, `competition_stats`, `biggest_wins`, `derbies`, `compare_seasons`, `search_players`, `player_profile`, `club_players`, `brazilian_players_overview`, `find_team`, `dataset_info` |
| brsoccer/server.py | Stdlib-only MCP JSON-RPC 2.0 server over stdio; wraps each query as a tool | `MCPServer`, `TOOLS`, `main()` |
| brsoccer/samples.py | Natural-language sample questions → (tool, args) mapping | sample question table |
| mcp_server.py | Thin top-level launcher delegating to `brsoccer.server` | module script |
| demo.py | Scripted demonstration of representative queries | module script |
| tests/conftest.py | Session-scoped read-only `db` fixture | `db` fixture |
| tests/test_data.py | Dataset loading/normalisation/merge correctness | 8 test functions |
| tests/test_teams.py | Team name normalisation & resolution | test functions |
| tests/test_queries.py | Computed-answer correctness for every query family | ~20 test functions |
| tests/test_server.py | MCP JSON-RPC dispatch + stdio end-to-end subprocess | test functions |
| tests/test_sample_questions.py | Natural-language questions driven through `tools/call` | parametrized |
| tests/test_performance.py | Latency budget (simple < 2s, aggregate < 5s) | test functions |
| tests/test_sdk_interop.py | Drives the server via the official MCP SDK client (importorskip) | test functions |
