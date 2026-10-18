# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2024-11-05`, capabilities.tools, serverInfo | `McpServer:initializeResult` |
| `ping` | `{}` | `McpServer:handle` |
| `tools/list` | tool definitions array | `McpServer:toolList` |
| `tools/call` | `{content:[{type:text}], isError}` | `McpServer:callTool` |

## MCP tools (SoccerTools)

| Tool | Purpose | Required args |
|------|---------|---------------|
| `search_matches` | Matches by team/opponent/venue/competition/season/stage/date range | (none) |
| `team_record` | W/D/L + goals for/against for a team | `team` |
| `head_to_head` | Head-to-head record + recent meetings between two teams | `team`, `opponent` |
| `standings` | League table computed from match results (3/1/0 pts) | `season` |
| `find_players` | FIFA players by name/nationality/club/position/min_overall | (none) |
| `club_player_summary` | Players-per-club count + avg overall for a nationality | (none) |
| `aggregate_stats` | goals_per_match, outcome_rates, biggest_wins, best_home_record, best_away_record | `metric` |

## Data schema (in-memory records)

- `Match`: date, competition, season, stage, home, away, homeGoals, awayGoals.
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey, height, weight.
- `TeamRecord`: team, played, wins, draws, losses, goalsFor, goalsAgainst (+ derived points, goalDifference, winRate).

## Data sources loaded (data/kaggle/)

Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv (both → Brasileirão Série A),
Brazilian_Cup_Matches.csv (Copa do Brasil), Libertadores_Matches.csv (Copa Libertadores),
BR-Football-Dataset.csv (extended stats), fifa_data.csv (players). All six files are read.
