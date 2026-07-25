# Architecture Summary — Brazilian Soccer MCP Server

> Written inline by `evaluate-run` (the `run-summary` skill is present in `skills/`
> but is not registered as an invocable skill in this session).

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 699 | FastMCP server + all data loading, normalization, and 5 query tools |
| `test_server.py` | 280 | 26 pytest/BDD-style tests across 6 test classes |

## Interfaces (MCP tools)

`server.py` builds a single `FastMCP(name="brazilian-soccer")` instance and registers
five `@mcp.tool()` async handlers, each returning `list[TextContent]`:

1. `query_matches(team, opponent, date_from, date_to, competition, season, limit)` — filter matches across 5 match datasets.
2. `query_team_stats(team, season, competition)` — aggregate W/L/D + goals for/against for a team.
3. `query_player(name, nationality, club, position, min_rating, limit)` — search the FIFA player dataset.
4. `query_competition(competition, season, team)` — list a competition's matches or per-team standings.
5. `analyze_statistics(statistic_type, team1, team2, season, competition, limit)` — `head_to_head`, `biggest_wins`, `avg_goals`, `home_record`.

The entrypoint (`__main__`) runs `mcp.run_stdio_async()` under `asyncio.run`.

## Supporting helpers

- `load_csv` / `load_all_data` — read the 6 CSVs from `data/kaggle/` (UTF-8, `errors="ignore"`). **Reloaded on every tool call** (no caching) — a performance concern for the < 2s / < 5s targets.
- `normalize_team_name` — lowercases, strips state suffix (`-SP`), strips common club suffixes, then maps through a ~40-entry `TEAM_NAME_MAP`.
- `parse_date` — tries 4 date formats; returns `datetime.min` on miss.
- `format_match_response` — renders a match line with multi-schema `.get(...)` fallbacks.

## Data flow

Each tool call → `load_all_data()` (re-reads all CSVs) → iterate rows → `normalize_team_name` on team columns → filter → format into a single `TextContent` string.

## Cross-cutting observations

- **Inconsistent case handling** is the dominant defect: `query_matches` and `query_team_stats` compare the *raw* argument against a *lowercased* normalized name, while `query_competition`, `analyze_statistics`, and `query_player.name` correctly `.lower()` the argument. See `findings.jsonl`.
- **No `requirements.txt`/`pyproject.toml`** — the `mcp` dependency is implicit.
- Every tool reloads ~24k CSV rows per call; no memoization.
