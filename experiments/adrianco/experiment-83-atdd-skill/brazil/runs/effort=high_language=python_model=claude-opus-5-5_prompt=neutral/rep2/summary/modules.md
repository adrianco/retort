# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `server.py` | MCP server; wraps the query engine as 17 MCP tools + 1 resource over stdio / streamable-HTTP | `mcp`, `main()`, `get_queries()` |
| `queries.py` | Query engine: match/team/player/competition/stats queries, standings, head-to-head, derbies, rankings | `SoccerQueries`, `QueryError`, `Record`, `StandingRow` |
| `data_loader.py` | Loads & normalizes the 6 Kaggle CSVs into `Match`/`Player` objects; team-name & date parsing, dedup | `SoccerData`, `Match`, `Player`, `get_data()`, `resolve_competition()`, `parse_date()` |
| `team_names.py` | Canonical team-name index, alias/variant normalization, derby definitions | name-normalization helpers, derby table |
| `tests/conftest.py` | Shared fixtures (session-scoped `SoccerData`/`SoccerQueries`) | fixtures |
| `tests/test_data_loader.py` | Loader + row-count + normalization tests (12 fns) | 12 test functions |
| `tests/test_queries.py` | Query-engine unit/integration tests (44 fns) | 44 test functions |
| `tests/test_team_names.py` | Team-name normalization tests (6 fns) | 6 test functions |
| `tests/test_sample_questions.py` | Acceptance suite: spec sample questions via in-process MCP `Client` (2 fns, parametrized) | 2 test functions |
| `tests/test_server.py` | MCP protocol contract + out-of-process stdio end-to-end (4 fns) | 4 test functions |
| `tests/test_performance.py` | Non-functional <2s / <5s latency targets (3 fns) | 3 test functions |

Source LOC (excl. tests/data): ~2087. Test LOC: ~762. 71 test functions → 182 parametrized cases.
