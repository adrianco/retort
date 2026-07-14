# Interfaces

## Transport

MCP (Model Context Protocol) over **stdio**, JSON-RPC 2.0, newline-delimited.
Diagnostics on stderr. Protocol revision `2024-11-05`.

## JSON-RPC methods

| Method | Returns |
|--------|---------|
| `initialize` | protocolVersion, capabilities.tools, serverInfo |
| `notifications/initialized` / `initialized` | (notification, no response) |
| `ping` | `{}` |
| `tools/list` | `{tools: [...]}` |
| `tools/call` | `{content: [{type:"text", text}], isError}` |

## MCP tools

| Tool | Args | Purpose |
|------|------|---------|
| `search_matches` | team, opponent, competition, season, home_only, away_only, start_date, end_date, limit | Match search (team/H2H/competition/season/date range) |
| `head_to_head` | team_a*, team_b*, limit | Aggregate H2H wins/draws/goals + match list |
| `team_record` | team*, season, competition, home_only, away_only | W/D/L, goals, points for a team |
| `standings` | season*, competition, limit | League table computed from match results |
| `search_players` | name, nationality, club, position, min_overall, limit | FIFA player search, rating-sorted |
| `competition_stats` | competition, season, top_n | Avg goals, home/away win rates, biggest wins |
| `list_competitions` | (none) | Discover valid competition filters |

(* = required argument)

## Data schema (in-memory)

`Match`: Competition, Season, Round, Stage, Stadium, Date/HasDate, HomeKey/AwayKey,
HomeGoals/AwayGoals/HasScore, shots/corners/HasStats, Source.

`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position,
JerseyNumber, Height, Weight, PreferredFoot.

`DB`: `Matches []Match`, `Players []Player`, `teams map[key]display`.

## Library API

The `soccer` package is a reusable query engine (`Load`, `DB.*` query methods);
the `mcp` package is a dependency-free JSON-RPC/MCP server wrapping it.
