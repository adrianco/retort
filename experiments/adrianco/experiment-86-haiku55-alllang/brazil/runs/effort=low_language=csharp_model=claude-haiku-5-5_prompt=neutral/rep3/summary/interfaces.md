# Interfaces

## HTTP routes

(none) — this is an MCP server over stdio, not an HTTP service.

## MCP tools (tools/call)

| Tool | Required args | Optional args | Returns |
|------|---------------|---------------|---------|
| `search_matches` | — | team, opponent, competition, season, date_from, date_to, venue, limit | Match list with head-to-head summary when team + opponent both given |
| `get_team_stats` | team | season, competition, venue | W/D/L record, goals for/against, win rate |
| `head_to_head` | team, opponent | — | H2H record, goals, recent meetings (up to 10) |
| `get_standings` | competition | season | League table (3/1/0 points), ordered by pts, wins, GD, GF |
| `get_league_stats` | — | competition, season | Goals/match, home/draw/away rates, 5 biggest wins, best home & away records |
| `search_players` | at least one of: name, nationality, club, position, min_overall | limit | FIFA players sorted by overall rating |

All tool results are returned as MCP `content` of type `text` with an `isError` flag. `ArgumentException` from bad input is surfaced to the model as an error result rather than crashing.

## JSON-RPC methods (MCP protocol)

| Method | Behaviour |
|--------|-----------|
| `initialize` | Returns protocolVersion `2024-11-05`, tools capability, serverInfo, instructions |
| `ping` | Empty result |
| `tools/list` | Lists the six tools with name, description, inputSchema |
| `tools/call` | Dispatches to the named tool handler |
| `notifications/*` | Accepted, no reply |

Transport: newline-delimited JSON-RPC 2.0 over stdin/stdout (UTF-8, no BOM); diagnostics go to stderr.

## CLI

`BrazilianSoccerMcp [data-dir]` — data directory from arg 1, else `SOCCER_DATA_DIR` env var, else `./data/kaggle`.

## Data schema (domain model)

- `Match`: Date, Competition, Season, Stage, Home/Away (`TeamRef` key+name), HomeGoals, AwayGoals; derived TotalGoals, Involves().
- `Player`: Id, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Value, Wage, Height, Weight, PreferredFoot, Skills (dictionary of 29 FIFA skill columns).
- `TeamStats`: Played, Wins, Draws, Losses, GoalsFor/Against; derived Points, GoalDifference, WinRate.

## Data sources

Six CSV files loaded from the data dir: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches) and `fifa_data.csv` (players). Duplicate matches across files are de-duplicated by a date/teams/score fingerprint.
