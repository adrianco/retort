# Architecture Summary

> Generated inline by `evaluate-run` (the `run-summary` skill was not registered as invocable in this session).

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 455 | MCP server. Defines 10 tools via `@server.list_tools()` and dispatches them in `@server.call_tool()`, formatting repository results into `TextContent`. |
| `repository.py` | 548 | `SoccerRepository` — query layer over pandas DataFrames: `search_matches`, `get_team_stats`, `get_head_to_head`, `search_players`, `get_league_standings`, `get_biggest_wins`, `get_average_goals`, `get_top_scorers`, `get_competitions`, `get_all_teams`. |
| `data_loader.py` | 367 | Loads the 6 Kaggle CSVs, normalizes 5 match datasets to a common schema (`home_team, away_team, home_goal, away_goal, date, season, round, stage, competition`), and provides `normalize_team_name` (large canonical map) and multi-format `parse_date`. |

## Flow

`main()` → `create_server()` → `SoccerRepository()` → `load_all_data()` reads CSVs into a unified `matches` DataFrame + `players` DataFrame. Tool calls filter/aggregate those DataFrames with pandas boolean masks. Team-name matching is done via case-insensitive substring `str.contains` plus a canonical-name map.

## Interfaces

- **MCP tools** (10): `search_matches`, `get_team_stats`, `get_head_to_head`, `search_players`, `get_league_standings`, `get_biggest_wins`, `get_average_goals`, `get_competitions`, `get_all_teams`, `get_top_scorers`.
- **Tests**: `tests/conftest.py` holds the pytest-bdd step definitions; `tests/*.feature` (20 scenarios) + `tests/test_repository.py` unit tests exercise the repository directly. `tests/steps/steps.py` is a dead duplicate of the step defs.

## Notable

- The server entrypoint (`main()` → `server.run_stdio()`) references a method the MCP SDK does not expose — the tools are correctly declared but the process cannot start (see findings R1).
- Tests validate the repository layer only; `server.py` handlers and `main()` are never invoked, so the broken entrypoint is not caught by the suite.
