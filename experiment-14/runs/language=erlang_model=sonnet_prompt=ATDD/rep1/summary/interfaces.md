# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdin/stdout)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities.tools, serverInfo | `soccer_mcp.erl:dispatch/2` |
| `tools/list` | `{tools: [...]}` (6 tools) | `soccer_mcp.erl:dispatch/2` → `soccer_tools:list/0` |
| `tools/call` | `{content: [{type:text, text:<json>}]}` | `soccer_mcp.erl:dispatch/2` → `soccer_tools:call/2` |

## MCP tools

| Tool | Args | Description |
|------|------|-------------|
| `find_matches` | team, competition, season, date_from, date_to, limit | Filter matches across all 5 match datasets |
| `get_team_stats` | team (req), competition, season | W/D/L record, goals for/against, home/away breakdown, win rate, points |
| `find_players` | name, nationality, club, position, min_rating, limit | FIFA player search, sorted by Overall desc |
| `get_head_to_head` | team1 (req), team2 (req), competition, season | H2H W/L/D + goals between two teams |
| `get_standings` | season (req), competition | Season standings computed from match results (3/1/0 pts) |
| `get_statistics` | stat_type (req), competition, season, limit | `biggest_wins`, `avg_goals`, `home_away_rates` aggregates |

## Data schema (loaded from data/kaggle/)

Internal match map: `home_team, away_team, home_goal, away_goal, competition, season, date, round`.
Sources: Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv, fifa_data.csv (players, raw binary-keyed columns).
