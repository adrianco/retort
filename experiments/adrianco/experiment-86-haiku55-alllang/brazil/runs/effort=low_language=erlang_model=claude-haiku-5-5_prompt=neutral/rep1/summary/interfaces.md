# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities, serverInfo | `soccer_mcp.erl:handle/2` |
| ping | `{}` | `soccer_mcp.erl:handle/2` |
| notifications/* | no reply | `soccer_mcp.erl:handle/2` |
| tools/list | tool definitions | `soccer_mcp.erl:handle/2` → `soccer_tools:definitions/0` |
| tools/call | text content (isError flag on bad args) | `soccer_mcp.erl:handle/2` → `soccer_tools:call/3` |

## MCP tools (tools/call `name`)

| Tool | Args | Backing query |
|------|------|---------------|
| search_matches | team, opponent, venue, season, competition, stage, date_from, date_to, limit | `soccer_stats:search/2` |
| team_record | team(req), season, competition, venue, … | `soccer_stats:record/2` |
| head_to_head | team(req), opponent(req), season, competition, limit | `soccer_stats:record/2` + `search/2` |
| standings | season(req), competition | `soccer_stats:standings/3` |
| league_summary | season, competition | `soccer_stats:league_summary/3` |
| biggest_wins | season, competition, limit | `soccer_stats:biggest_wins/3` |
| search_players | name, nationality, club, position, min_overall, limit | `soccer_stats:search_players/2` |
| club_summary | nationality, limit | `soccer_stats:club_summary/2` |

## Data schema (normalized)

`match`: source, date (YYYYMMDD int), season, competition, stage, round, home, away, home_tokens, away_tokens, home_goals, away_goals.

`player`: name, name_tokens, age, nationality, nationality_tokens, overall, potential, club, club_tokens, position.

## Data sources

Loads 6 CSVs from `data/kaggle/`: Brasileirao_Matches, novo_campeonato_brasileiro (historical), Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset (match files), fifa_data (players).
