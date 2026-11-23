# Interfaces

## MCP tools (JSON-RPC over stdio)

The server registers 11 read-only tools (`server.py:11` `TOOL_NAMES`), each generated
from a `Soccer` method signature (`server.py:tool_schema`). All carry
`annotations: {readOnlyHint: true, openWorldHint: false}`.

| Tool | Returns | Handler |
|------|---------|---------|
| search_matches | paged matches filtered by team/opponent/venue/competition/season/date/stage/round/derbies/source | `soccer.py:search_matches` |
| team_stats | W/L/D, goals for/against, win %, with by-competition/season/venue breakdowns | `soccer.py:team_stats` |
| head_to_head | both teams' records + paged meetings | `soccer.py:head_to_head` |
| search_players | paged FIFA players by name/nationality/club/position, Overall-sorted | `soccer.py:search_players` |
| standings | league table computed from match results, completeness + relegation flags | `soccer.py:standings` |
| tournament_bracket | knockout fixtures grouped by stage/round | `soccer.py:tournament_bracket` |
| match_statistics | avg goals, home/away/draw rates, biggest wins, by season | `soccer.py:match_statistics` |
| team_rankings | teams ranked by points/goals_for/wins/win_rate | `soccer.py:team_rankings` |
| club_profile | join of a club's match record + FIFA snapshot players | `soccer.py:club_profile` |
| top_scorers | availability stub (datasets record team scores only) | `soccer.py:top_scorers` |
| coverage | per-source row counts + merged fixture total | `soccer.py:coverage` |

## JSON-RPC methods

| Method | Behavior |
|--------|----------|
| initialize | negotiates protocolVersion (4 supported), returns serverInfo + instructions |
| notifications/initialized | sets `ready` |
| tools/list | returns the 11 tool schemas |
| tools/call | binds+type-checks arguments, returns `content` text (+ `structuredContent` on 2025-06-18/2025-11-25) |
| ping | returns `{}` |

## Data schema (inputs)

Six CSVs in `data/kaggle/`: `Brasileirao_Matches.csv` (4,180), `novo_campeonato_brasileiro.csv`
(6,886), `Brazilian_Cup_Matches.csv` (1,337), `Libertadores_Matches.csv` (1,255),
`BR-Football-Dataset.csv` (10,296 extended stats), `fifa_data.csv` (18,207 players).
Matches merge into a single deduplicated fixture list keyed on `(competition, home, away)`.
