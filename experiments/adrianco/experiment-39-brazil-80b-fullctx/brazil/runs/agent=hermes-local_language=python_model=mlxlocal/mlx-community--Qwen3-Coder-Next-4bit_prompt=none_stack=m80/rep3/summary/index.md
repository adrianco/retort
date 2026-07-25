# Architecture Summary

_Generated inline (the `run-summary` skill was not invoked in this evaluation)._

## Modules

| File | Role |
|------|------|
| `soccer_data.py` | `SoccerDataLoader` — reads the 6 Kaggle CSVs from `data/kaggle/`, normalizes team names, tags each match df with a `competition` column. Singleton via `get_loader()`. |
| `match_queries.py` | `MatchQueryEngine` — `find_matches` (team/competition/season/date-range filters), `get_head_to_head`, `get_team_match_history`. Concatenates all match dfs. |
| `player_queries.py` | `PlayerQueryEngine` — `find_players` over the FIFA dataset (name/nationality/club/position/rating filters). |
| `team_queries.py` | `TeamQueryEngine` — `get_team_statistics` (W/L/D, goals, home/away split), `get_team_head_to_head`, `get_team_players`, `get_top_scorers`. |
| `competition_queries.py` | `CompetitionQueryEngine` — `get_competition_standings` (points table from matches), `get_champion`, `get_relegated_teams`, Libertadores bracket. |
| `statistical_analysis.py` | `StatisticalAnalysisEngine` — avg goals/match, home advantage, biggest victories, win-rate rankings, season comparison. |
| `test_brazilian_soccer.py` / `test_sample_questions.py` | 56 pytest tests exercising the engines directly. |

## Flow

CSV files → `SoccerDataLoader.load_all()` → per-domain query engines (each holds a loader + upstream engines via singletons) → plain Python dicts/lists returned to callers.

## Key observation

Every module docstring says "MCP Server", but **no MCP protocol layer exists** — there is no server entrypoint, no `mcp`/`FastMCP` import, and no tool/resource registration. The deliverable is a library of query engines, not the MCP server the spec asks for. Tests import the engine classes directly rather than going through any server.
