# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Key args | Returns | Handler |
|------|----------|---------|---------|
| find_matches | team1, team2, season, competition, limit | Match list + head-to-head summary (text) | `tools/find_matches.ex:call/1` |
| get_team_stats | team (req), season, competition | W/D/L, goals for/against, win rate, points (text) | `tools/get_team_stats.ex:call/1` |
| find_players | name, nationality, club, position, min_overall, limit | Ranked player list with Overall/Club/Nationality (text) | `tools/find_players.ex:call/1` |
| get_competition_standings | competition (req), season (req) | Computed league table: pts, W/D/L, GF/GA/GD (text) | `tools/get_competition_standings.ex:call/1` |
| get_statistics | stat_type (req: biggest_wins\|goals_per_match\|home_away_record\|best_home_teams), competition, season | Aggregate stat report (text) | `tools/get_statistics.ex:call/1` |

## MCP protocol methods

| Method | Behavior | Handler |
|--------|----------|---------|
| initialize | Returns protocolVersion 2024-11-05, serverInfo, capabilities | `server.ex:22` |
| initialized | No-op notification | `server.ex:31` |
| tools/list | Lists the 5 tools with name/description/inputSchema | `server.ex:33` |
| tools/call | Dispatches to the tool modules above | `server.ex:37` |

Transport: newline-delimited JSON-RPC over stdin/stdout (`stdio_runner.ex`). No official MCP SDK; the JSON-RPC layer is hand-rolled.

## Data schema (in-memory ETS, loaded from `data/kaggle/*.csv`)

- `:brasileirao`, `:cup`, `:libertadores`, `:historico` — match tuples {home, away, date, home_goal, away_goal, season, round/stage, competition}
- `:br_football` — {home, away, date, home_goal, away_goal, tournament}
- `:fifa` — {name, age, nationality, overall, potential, club}

## HTTP routes / CLI commands

(none)
