# Interfaces

The generated code exposes the same query surface through two independent layers: an MCP tool server (`src/mcp_server.py`) and a FastAPI HTTP app (`src/api.py`). Both delegate to `QueryEngine` in `src/data_utils.py`.

## MCP tools

Registered via `@mcp.tool()` on the `FastMCP` instance `mcp` (name `brazilian-soccer-mcp-server`). All return a JSON string.

| Tool | Args | Description |
|------|------|-------------|
| find_matches_by_teams | team1, team2?, season?, competition?, limit=100 | Matches for one or two teams, optionally filtered |
| get_match_by_id | match_id | Single match by `id` (linear scan) |
| get_team_stats | team, season?, competition? | Aggregated W/D/L, goals, home/away splits |
| get_team_comparison | team1, team2 | Head-to-head record and per-match details |
| search_players | name?, club?, nationality?, position?, limit=100 | Player search by any combination of filters |
| get_top_brazilian_players | limit=10 | Brazilian players sorted by `overall` |
| get_competition_standings | competition, season | League table computed from match results |
| get_big_wins | competition?, limit=10 | Matches with goal difference >= 3, sorted |
| get_average_goals_per_match | competition? | Mean total goals per match |
| get_home_win_rate | (none) | Home win % over decisive matches |
| list_competitions | (none) | Distinct competition names |
| list_seasons | competition? | Distinct season years |

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | / | Server info + endpoint list | `api.py:root` |
| GET | /health | `{status, version}` | `api.py:health_check` |
| GET | /api/matches | `QueryResponse` | `api.py:get_matches` |
| GET | /api/matches/{match_id} | `QueryResponse \| 404` | `api.py:get_match` |
| GET | /api/teams/stats | `TeamStats` | `api.py:get_team_stats` |
| GET | /api/teams/comparison | `TeamComparison` | `api.py:get_team_comparison` |
| GET | /api/players/search | `QueryResponse` | `api.py:search_players` |
| GET | /api/players/brazilian/top | `QueryResponse` | `api.py:get_top_brazilian_players` |
| GET | /api/competitions/standings | `QueryResponse` | `api.py:get_competition_standings` |
| GET | /api/stats/big-wins | `QueryResponse` | `api.py:get_big_wins` |
| GET | /api/stats/average-goals | `QueryResponse` | `api.py:get_average_goals` |
| GET | /api/stats/home-win-rate | `QueryResponse` | `api.py:get_home_win_rate` |

Note: `MatchQueryRequest`, `TeamStatsRequest`, `TeamComparisonRequest`, `PlayerSearchRequest`, `CompetitionStandingsRequest` Pydantic models are declared but unused — all routes take query params, not request bodies.

## CLI

`python -m src.mcp_server` (via `main()`): flags `--stdio` (stdio transport) and `--mount-path` (default `/`, for SSE). `python -m src.main` launches the FastAPI app on `0.0.0.0:8000` with reload.

## Data schema

Loaded from six CSVs in `data/kaggle/` into two flat in-memory lists on `DataLoader`:

- `matches: List[Match]` — merged from Brasileirão, Copa do Brasil, Libertadores, BR-Football extended stats, and historical Brasileirão (2003-2019). Key fields: `home_team`, `away_team`, `home_goal`, `away_goal`, `season`, `round`, `competition`, plus optional extended stats (corners, shots, attacks) and metadata (arena, winner, stage).
- `players: List[Player]` — from `fifa_data.csv`. Key fields: `id`, `name`, `nationality`, `overall`, `club`, `position`, plus ~40 detailed skill ratings.

`Match.id` is never populated (always `None`), so `get_match_by_id` and `/api/matches/{id}` never match.
