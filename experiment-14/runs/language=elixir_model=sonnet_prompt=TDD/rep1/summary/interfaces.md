# Interfaces

## MCP tools (JSON-RPC over stdio)

Exposed via `tools/list`; invoked via `tools/call`. Defined in `mcp/tools.ex:definitions/0`, dispatched by `mcp/tools.ex:call/2`.

| Tool | Inputs | Returns | Backed by |
|------|--------|---------|-----------|
| `search_matches` | team, team2, competition, season, from_date, to_date, limit | formatted match list | `Queries.Matches.*` |
| `get_team_stats` | team* , season, competition, home_only | W/D/L, goals for/against, win rate | `Queries.Teams.team_record/2` |
| `search_players` | name, nationality, club, position, top, limit | player list with ratings | `Queries.Players.*` |
| `get_standings` | season*, competition* | computed standings table | `Queries.Teams.competition_standings/2` |
| `head_to_head` | team1*, team2*, limit | H2H W/D/L + recent matches | `Queries.Matches.search_by_teams/2` |
| `biggest_wins` | limit, competition | biggest-margin matches | `Queries.Matches.biggest_wins/1` |
| `competition_stats` | competition, season | avg goals/match, home-win rate, top scorers | `Queries.Teams.*` |

(* = required input per JSON schema)

## MCP protocol methods (`mcp/server.ex`)

`initialize`, `notifications/initialized`, `tools/list`, `tools/call`; unknown methods → JSON-RPC error -32601; parse errors → -32700. Protocol version `2024-11-05`.

## Data schema (in-memory ETS)

- **matches** (`:bag`): `{datetime, home_team, away_team, home_goal, away_goal, season, round, competition, stage}` — loaded from 5 match CSVs, team names normalized (state suffix stripped).
- **players** (`:set`, keyed by id): `{id, name, age, nationality, overall, potential, club, position, jersey}` — loaded from `fifa_data.csv`.
