# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo | `BSMCPServer:handleMessage:` |
| ping | `{}` | `BSMCPServer:handleMessage:` |
| tools/list | `{tools: [...15 tool schemas]}` | `BSMCPServer:handleMessage:` |
| tools/call | `{content:[{type:text}], isError}` | `BSTools:callTool:arguments:isError:` |
| notifications/* | (no reply) | `BSMCPServer:handleMessage:` |

Standard JSON-RPC errors returned: -32700 parse, -32600 invalid request, -32601 method not found, -32602 invalid params.

## MCP tools (15)

| Tool | Purpose |
|------|---------|
| search_matches | Matches by team, opponent, competition, season, date range, venue |
| head_to_head | H2H record + recent matches between two teams |
| team_stats | W/D/L record and goals for a team (by season/competition/venue) |
| standings | Season league table computed from match results |
| search_players | FIFA players by name, nationality, club, position, min rating |
| competition_stats | Aggregate: matches, avg goals/match, home/away/draw rates |
| biggest_wins | Largest victory margins |
| rank_teams | Rank by win_rate/points/wins/goals_for/goals_against/goal_diff |
| cup_finals | Copa do Brasil / Libertadores finals |
| knockout_bracket | Knockout-stage matches for a cup season |
| derbies | Traditional derby matches (Fla-Flu, Grenal, ...) |
| team_competitions | Competitions a team has appeared in |
| compare_seasons | Aggregate stats + champions of two seasons |
| brazilian_clubs_players | FIFA players at Brazilian clubs (cross-file query) |
| dataset_info | Row counts per CSV + seasons covered per competition |

## CLI

`brazilian-soccer-mcp` — run MCP stdio server.
`brazilian-soccer-mcp <tool> '<json-args>'` — run one tool and print its text answer.
Env: `BS_DATA_DIR` overrides the default `data/kaggle` directory.

## Data schema

- `BSMatch`: homeKey, awayKey, homeTeam, awayTeam, homeGoals, awayGoals, date (YYYY-MM-DD), time, season, round, competition, stage, source.
- `BSPlayer`: name, overall, potential, nationality, club, position, jerseyNumber, height, weight, value, skills{}.
- `BSTeamRecord`: team, matches, wins, draws, losses, goalsFor, goalsAgainst, points (W*3+D), goalDifference, winRate.

Source CSVs (data/kaggle/): Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv, fifa_data.csv.
