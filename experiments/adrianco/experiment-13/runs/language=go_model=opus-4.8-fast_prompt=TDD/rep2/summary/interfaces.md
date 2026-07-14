# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Find matches by team/opponent/home/away, competition, season, season range, date range | `team`, `opponent`, `home_team`, `away_team`, `competition`, `season`, `season_from`, `season_to`, `date_from`, `date_to`, `limit` |
| `head_to_head` | W/D/L + meeting list between two teams | `team1`*, `team2`* , `limit` |
| `team_record` | W/D/L, goals for/against, points, win rate for a team | `team`*, `competition`, `season`, `home_only`, `away_only` |
| `search_players` | Search FIFA players by name/nationality/club/position/min rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `standings` | League table computed from match results | `competition`*, `season`* |
| `competition_stats` | Aggregate stats: avg goals, home/away/draw rates, biggest wins | `competition`, `season`, `limit` |

(* = required in inputSchema)

## MCP protocol methods

| Method | Handled |
|--------|---------|
| `initialize` | returns protocolVersion `2024-11-05`, serverInfo, tools capability |
| `tools/list` | returns the 6 tool descriptors above |
| `tools/call` | dispatches to the handlers; tool errors returned as `isError` text content |
| `ping` | empty result |
| `notifications/initialized`, `notifications/cancelled` | no response (notification) |

Unknown methods with an `id` return JSON-RPC error `-32601` (method not found). Transport: newline/stream-delimited JSON-RPC 2.0 over stdin/stdout.

## CLI

`brazilian-soccer-mcp [-data DIR]` — `-data` defaults to `data/kaggle`. Progress/errors on stderr; protocol stream on stdout.

## Data schema (in-memory)

- `Match`: Competition, Season, Round, Stage, Date/HasDate, HomeTeam, AwayTeam, HomeGoals/AwayGoals/HasScore, Stadium, Source, plus corners/shots (BR-Football only).
- `Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.
- Sources loaded: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro (matches); fifa_data (players).
