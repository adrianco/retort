# Interfaces

## Transport

**FastAPI REST over HTTP** (uvicorn, port 8000). **Not** MCP — no `mcp`/`fastmcp` import,
no tool/resource registration, no stdio JSON-RPC.

## HTTP routes

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/`            | Metadata + `data_loaded` flag |
| POST | `/matches`     | Filter matches by team1/team2/season/competition/(date_from/date_to — declared but ignored) |
| POST | `/teams`       | Team stats (W/L/D, goals for/against), opponents, recent matches |
| POST | `/players`     | Filter FIFA players by name/nationality/club/position/min_overall |
| POST | `/competitions`| Standings + inferred top-scorers for a competition+season |
| POST | `/stats`       | `average_goals` \| `home_record` \| `biggest_wins` \| `top_scorers` |

## Request schemas (pydantic)

- `MatchQuery{team1, team2, season, competition, date_from, date_to, limit}` — `date_from`/`date_to` are accepted but never applied.
- `TeamQuery{team, season, competition}`
- `PlayerQuery{name, nationality, club, position, min_overall, limit}`
- `CompetitionQuery{competition, season, limit}`
- `StatisticalQuery{metric, competition, season}`

## Data schema

Six pandas DataFrames in `DATA`: `brasileirao`, `copa_brasil`, `libertadores`,
`br_football`, `brasileirao_hist`, `fifa`. Match frames are concatenated per request;
the concatenation carries no competition label, so `competition` filtering relies on
substring matches against heterogeneous `tournament`/`round`/`stage` columns.
