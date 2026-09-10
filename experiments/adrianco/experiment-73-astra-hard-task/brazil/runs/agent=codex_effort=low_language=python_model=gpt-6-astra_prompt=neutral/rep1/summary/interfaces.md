# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

Lifecycle: `initialize` → `notifications/initialized` → `tools/list` / `tools/call`; also `ping`. Tool calls before `notifications/initialized` are rejected with `-32002`. Negotiates protocol versions `2025-11-25`, `2025-06-18`, `2025-03-26`, `2024-11-05`.

## MCP tools (registered in `TOOLS`, schemas derived from method signatures)

| Tool | Returns | Handler |
|------|---------|---------|
| search_matches | paginated matches (team/opponent/venue/competition/season/date range/stage/source filters) | `soccer.py:SoccerGraph.search_matches` |
| get_match | one match with source rows + provenance | `soccer.py:SoccerGraph.get_match` |
| team_statistics | W/D/L, goals, home/away splits, per-competition breakdown, club players | `soccer.py:SoccerGraph.team_statistics` |
| head_to_head | both teams' records + latest meeting | `soccer.py:SoccerGraph.head_to_head` |
| search_players | FIFA snapshot by name/nationality/club/position/min_overall | `soccer.py:SoccerGraph.search_players` |
| standings | league table computed from match results (3pts/win) | `soccer.py:SoccerGraph.standings` |
| competition_bracket | cup ties grouped by stage | `soccer.py:SoccerGraph.competition_bracket` |
| statistics | goals/match, home-win rate, biggest wins, team rankings | `soccer.py:SoccerGraph.statistics` |
| season_trends | compare stats across seasons | `soccer.py:SoccerGraph.season_trends` |
| derbies | curated traditional rivalries | `soccer.py:SoccerGraph.derbies` |
| competitions | observed competitions/seasons/counts | `soccer.py:SoccerGraph.competitions` |
| graph_neighbors | knowledge-graph nodes/edges around a team | `soccer.py:SoccerGraph.graph_neighbors` |
| data_status | source load/reject counts, dedup, coverage, limitations | `soccer.py:SoccerGraph.data_status` |

## CLI

`python server.py [--data-dir PATH]` — starts the stdio server. `python build.py [--output PATH]` — builds the zipapp.

## Data schema

Match record: `id` (sha256 of competition|date|home|away), `date`, `season`, `competition`, `home_team`, `away_team`, `home_goal`, `away_goal`, `round`, `stage`, `stadium`, `statistics`, `sources[]`. Player record: `id`, `name`, `age`, `nationality`, `overall`, `potential`, `club`, `position`, `attributes`, `source`.
