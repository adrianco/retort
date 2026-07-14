# Interfaces

## MCP / JSON-RPC methods (stdio transport)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | server info + capabilities | `mcp::server_info` |
| `notifications/initialized` / `initialized` | (no response) | `process_request` |
| `tools/list` | array of 8 tool definitions | `mcp::tool_definitions` |
| `tools/call` | `{content:[{type:"text",text}]}` | `handle_tool_call` |
| `ping` | `{}` | `process_request` |

## MCP tools exposed

| Tool | Required args | Optional args | Backing fn |
|------|---------------|---------------|------------|
| `search_matches` | — | team, team2, competition, season, date_from, date_to, limit | `tools::search_matches` |
| `team_stats` | team | competition, season | `tools::team_stats` |
| `head_to_head` | team1, team2 | competition, season, limit | `tools::head_to_head` |
| `search_players` | — | name, nationality, club, position, min_overall, max_results | `tools::search_players` |
| `season_standings` | competition, season | limit | `tools::season_standings` |
| `biggest_wins` | — | competition, season, limit | `tools::biggest_wins` |
| `competition_stats` | — | competition, season | `tools::competition_stats` |
| `top_scoring_teams` | — | competition, season, limit | `tools::top_scoring_teams` |

## Data schema (in-memory, loaded from data/kaggle/*.csv)

`Match`: datetime, home_team, away_team, home_goal, away_goal, season, competition, round, stage, arena, corner/shots/attacks stats (BR-Football only).

`Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, value, wage.

Six CSV sources mapped to a unified `competition` label: Brasileirão Serie A, Copa do Brasil, Copa Libertadores, BR-Football (tournament column), Brasileirão (Historical), FIFA players.
