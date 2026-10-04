# Interfaces

## MCP protocol (stdio, JSON-RPC 2.0)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo | `server.py:handle` |
| ping | `{}` | `server.py:handle` |
| tools/list | list of 20 tool definitions (name, description, inputSchema) | `server.py:handle` |
| tools/call | `{content:[{type:text}], isError}` (tool errors reported in-band) | `server.py:handle` → `call_tool` |

Unknown method → JSON-RPC error `-32601`; parse error → `-32700`; notifications (no id) → no response.

## MCP tools (20)

| Tool | Purpose |
|------|---------|
| search_matches | matches by team/opponent/venue/competition/season/date-range/stage |
| last_match | most recent match of a team (optionally vs opponent) |
| head_to_head | head-to-head W/L/D and goals between two teams |
| team_record | W/D/L and goals for/against for a team |
| standings | league table for a season, computed from matches |
| champion | winner of a competition in a season |
| relegated | bottom-4 of the Brasileirão for a season |
| cup_finals | Copa do Brasil / Libertadores finals |
| bracket | knockout bracket of a cup for a season |
| derbies | traditional rivalry matches (Fla-Flu, Grenal, …) |
| team_competitions | competitions a team played, with counts |
| league_stats | goals/match, home/away/draw rates |
| compare_seasons | aggregate stats of two seasons |
| biggest_wins | largest victory margins |
| best_records | best home/away/overall win-rate teams |
| top_scoring_teams | teams scoring the most goals |
| search_players | FIFA players by name/nationality/club/position/rating |
| brazilian_clubs_players | count/avg rating of Brazilian players per Brazilian club |
| team_profile | cross-dataset: match record + FIFA squad |

## Data schema

In-memory `Match` dataclass: `date, home, away, home_goal, away_goal, competition, season, round, source, extra`. Teams normalized to canonical keys (accents/suffixes/aliases stripped) via `normalize_team`. Players kept as FIFA-CSV dict rows plus `_name_key`/`_club_key`.

Data sources: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv` (18,207 players).

## CLI / HTTP

(none) — stdio MCP only; run via `python3 server.py`.
