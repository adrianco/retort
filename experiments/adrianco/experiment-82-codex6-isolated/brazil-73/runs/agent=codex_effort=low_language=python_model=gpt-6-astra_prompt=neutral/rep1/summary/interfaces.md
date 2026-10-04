# Interfaces

## MCP tools (JSON-RPC over stdio, protocol rev 2025-11-25)

Registered in `server.py:SCHEMAS`, dispatched to `SoccerGraph` methods:

| Tool | Required args | Purpose | Handler |
|------|---------------|---------|---------|
| search_matches | (none) | Filter matches by team/opponent/venue/competition/season/date range/stage/source; paginated | `soccer.py:SoccerGraph.search_matches` |
| team_statistics | team | W/D/L, goals, points, win rate; per-competition breakdown | `soccer.py:team_statistics` |
| head_to_head | team, opponent | Head-to-head record from team's perspective | `soccer.py:head_to_head` |
| search_players | (none) | FIFA player search by name/nationality/club/position/min_rating | `soccer.py:search_players` |
| standings | competition, season | Season table computed from match results | `soccer.py:standings` |
| analysis | (none) | Aggregate goal averages, home/away, biggest wins, season trends | `soccer.py:analysis` |
| team_profile | team | Cross-file stats + competitions + FIFA snapshot players | `soccer.py:team_profile` |
| competition_bracket | competition, season | Fixtures grouped by stage | `soccer.py:competition_bracket` |
| derbies | (none) | Curated traditional rivalry fixtures | `soccer.py:derbies` |
| graph_neighbors | node_id | Traverse typed graph edges | `soccer.py:graph_neighbors` |
| coverage | (none) | Data provenance, counts, import issues, limitations | `soccer.py:coverage` |

MCP methods handled: `initialize`, `ping`, `tools/list`, `tools/call`, notifications (no-id → no response). JSON-RPC errors: -32700 parse, -32600 invalid request, -32601 method not found, -32602 invalid params, -32000 uninitialized.

## Library API (`soccer.SoccerGraph`)

Public query methods listed above, plus internal `_select()` (shared filter generator), `_page()` (pagination), `_match()` (per-file row parsing). Module helpers: `team_name()` (alias/state-suffix normalization), `competition_name()`, `date_value()` (multi-format dates), `number()`, `fold()` (accent folding).

## Data schema (in-memory)

- **match**: date, home_team, away_team, home_goal, away_goal, season, competition, round, stage, stadium, statistics, id, sources[] (cross-source provenance, deduplicated).
- **player**: id, name, nationality, club, position, overall, potential, age, attributes.
- **graph nodes/edges**: HOME_TEAM, AWAY_TEAM, IN_COMPETITION, IN_SEASON, HAS_MATCH, PLAYS_FOR_SNAPSHOT, HAS_PLAYER_SNAPSHOT.
