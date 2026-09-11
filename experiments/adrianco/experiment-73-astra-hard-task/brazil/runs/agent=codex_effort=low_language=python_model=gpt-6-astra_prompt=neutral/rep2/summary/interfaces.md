# Interfaces

## MCP tools (JSON-RPC `tools/call`)

11 tools registered in `server.py:DEFINITIONS`, dispatched to `SoccerGraph` methods:

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Fixtures/results across all 5 match files; team/venue/competition/season/date-range/stage filters, paging, `latest` | `soccer.py:search_matches` |
| search_players | FIFA player search by name/nationality/club/position, rating-sorted, paged | `soccer.py:search_players` |
| standings | Points/W-L-D table computed from matches; venue filter for home/away tables | `soccer.py:standings` |
| team_info | Team record + competitions + FIFA roster (cross-file) | `soccer.py:team_info` |
| head_to_head | Two-team W/D/L record + fixtures | `soccer.py:head_to_head` |
| statistics | Average goals, home-win %, biggest victories | `soccer.py:statistics` |
| trends | Per-season aggregates for a team/competition | `soccer.py:trends` |
| bracket | Cup fixtures grouped by stage/round (no invented advancement) | `soccer.py:bracket` |
| top_scorers | Honest unavailability explanation (no per-player goal events in data) | `soccer.py:top_scorers` |
| graph | Bounded knowledge graph (teams/players/matches/competitions, typed edges) | `soccer.py:graph` |
| coverage | Source row counts, date span, dedup/ingestion diagnostics | `soccer.py:coverage` |

## JSON-RPC protocol (`server.py:Server.handle`)

| Method | Behavior |
|--------|----------|
| initialize | Negotiates protocolVersion (2024-11-05 / 2025-03-26 / 2025-06-18), returns serverInfo + instructions |
| ping | `{}` |
| tools/list | Returns the 11 tool schemas |
| tools/call | Validates args against schema, invokes graph method, wraps result as text content; errors → `isError:true` |
| notifications/* (no id) | Treated as notification → no response |

Error codes: -32700 parse, -32600 invalid request, -32601 method not found, -32602 bad params.

## Data schema (in-memory)

- **match**: `date`, `home_team`, `away_team` (normalized keys), `competition`, `season`, `home_goal`, `away_goal`, `round`, `stage`, `stadium`, `sources[]`, `source_rows{}`.
- **player**: `id`, `name`, `club`, `team` (normalized), `nationality`, `position`, `overall`, `potential`, `attributes` (raw row).

## CLI

`python server.py [--data-dir DIR]` — MCP server over stdin/stdout.
