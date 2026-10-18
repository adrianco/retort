# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Purpose | Handler |
|------|---------|---------|
| find_matches | Matches by team/opponent/venue/competition/season/date range | `tools.py:_find_matches` |
| head_to_head | W/D/L and meetings between two teams | `tools.py:_head_to_head` |
| team_stats | W/D/L + goals for/against for one team (filterable) | `tools.py:_team_stats` |
| standings | League table for a season, computed from matches | `tools.py:_standings` |
| league_stats | Avg goals/match, home win rate, optional biggest wins | `tools.py:_league_stats` |
| best_away_records | Teams ranked by away win rate | `tools.py:_best_away` |
| search_players | FIFA players by name/nationality/club/position/min overall | `tools.py:_search_players` |
| brazilian_players_by_club | Brazilian players per Brazilian club with avg rating | `tools.py:_brazilian_clubs` |

## MCP protocol methods

`initialize`, `ping`, `tools/list`, `tools/call`, `notifications/*` (no-op). JSON-RPC 2.0 over stdio, one message per line.

## CLI

`python -m brazsoccer_mcp [--data-dir PATH]` — `BRAZSOCCER_DATA_DIR` env override; logs to stderr, serves MCP on stdout.

## Data schema (in-memory)

- `Match`: date, competition, home/away, home_key/away_key, home_goals/away_goals, season, source, round?, stage?
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, value, wage, preferred_foot, attributes{skill:int}
