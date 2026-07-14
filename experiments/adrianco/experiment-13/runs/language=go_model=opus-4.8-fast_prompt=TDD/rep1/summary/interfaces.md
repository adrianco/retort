# Interfaces

## MCP Protocol (JSON-RPC 2.0 over stdio)

| Method | Direction | Purpose |
|--------|-----------|---------|
| initialize | request | Handshake — returns protocolVersion, capabilities, serverInfo |
| notifications/initialized | notification | Client acknowledgment (no response) |
| ping | request | Health check — returns `{}` |
| tools/list | request | Returns catalog of 6 tools with JSON-Schema |
| tools/call | request | Invokes a tool by name with arguments |

## MCP Tools

| Tool | Required args | Optional args | Returns |
|------|---------------|---------------|---------|
| search_matches | — | team, opponent, competition, season, source, limit | Dated match list with scores |
| team_record | team | season, competition, source, venue | W/L/D record with goals and win rate |
| head_to_head | team_a, team_b | — | H2H summary with recent meetings |
| standings | season | competition | League table with points/GD |
| search_players | — | name, nationality, club, position, min_overall, limit | Ranked player list by overall rating |
| competition_stats | — | competition, season, source | Aggregate stats + biggest victories |

## Data Schema (in-memory)

- `Match`: Source, Competition, Date, Season, Round, Stage, Arena, HomeTeam/AwayTeam (display + normalized key), HomeGoals/AwayGoals, HasScore/HasDate
- `Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight
- `Dataset`: `[]Match` + `[]Player`

## CLI

```
brazilsoccer [data-dir]    # data-dir defaults to ./data/kaggle or $BR_SOCCER_DATA
```

Reads newline-delimited JSON-RPC from stdin, writes responses to stdout, diagnostics to stderr.
