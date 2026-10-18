# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2024-11-05`, capabilities, serverInfo | `server.py:handle_message` |
| `ping` | `{}` | `server.py:handle_message` |
| `tools/list` | the 11 tool definitions | `SoccerTools.describe` |
| `tools/call` | `{content:[{type:"text",text}], isError}` | `SoccerTools.call` |

## MCP tools

| Tool | Purpose | Handler |
|------|---------|---------|
| `find_matches` | matches by team/opponent/date-range/competition/season/venue | `queries.py:find_matches` |
| `team_record` | W/D/L, goals for/against, win rate (by season/competition/venue) | `queries.py:team_record` |
| `head_to_head` | head-to-head record between two teams | `queries.py:head_to_head` |
| `standings` | league table computed from match results (3pts/win) | `queries.py:standings` |
| `season_stats` | goals/match, home/draw/away rates | `queries.py:season_stats` |
| `biggest_wins` | largest winning margins | `queries.py:biggest_wins` |
| `venue_ranking` | teams ranked by home/away win rate | `queries.py:venue_ranking` |
| `search_players` | FIFA players by (partial) name | `queries.py:search_players` |
| `list_players` | players filtered by nationality/club/position | `queries.py:list_players` |
| `club_profile` | squad size, avg rating, top players for a club | `queries.py:club_profile` |

## Library API

`SoccerKnowledgeBase.load(data_dir)` builds the KB from the six CSVs. Query methods return
frozen dataclasses (`TeamRecord`, `HeadToHead`, `SeasonStats`) or `list[Match]` / `list[Player]`.

## Data schema (in-memory)

- `Match`: played_on, competition, season, stage, home/away `Team`, home_goals, away_goals, source.
- `Team`: key (normalized), state, name (display).
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number.

## CLI

`python -m brazilian_soccer_mcp.server [--data-dir PATH]` — starts the stdio MCP server.
