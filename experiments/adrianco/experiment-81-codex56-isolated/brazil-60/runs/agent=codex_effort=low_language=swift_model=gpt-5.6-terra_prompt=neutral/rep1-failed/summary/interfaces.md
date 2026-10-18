# Interfaces

## MCP transport

Newline-delimited JSON-RPC 2.0 over stdin/stdout (hand-rolled, no MCP SDK). Methods handled: `initialize`, `tools/list`, `tools/call`, `ping`. Unknown methods return JSON-RPC error `-32601`.

## MCP tools

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| `search_matches` | team, opponent, competition, season, from, to, limit | `{count, matches[]}` | `SoccerStore.findMatches` |
| `team_statistics` | team (req), season, competition, home_only | W/L/D + goals + points + win_rate | `SoccerStore.teamRecord` |
| `head_to_head` | team (req), opponent (req), season | `{matches, wins, losses, draws, recent_matches[]}` | `SoccerStore.headToHead` |
| `search_players` | name, nationality, club, position, limit | `{count, players[]}` | `SoccerStore.searchPlayers` |
| `standings` | season (req), competition | `{season, competition, standings[]}` | `SoccerStore.standings` |
| `data_summary` | (none) | record + source counts | inline in `handle` |

## Data schema

`Match`: date, home, away, homeGoals, awayGoals, competition, season?, round?, source.
`Player`: name, nationality, club, position, overall?, potential?, age?.
`Record`: played, wins, draws, losses, goalsFor, goalsAgainst, points (3·W+D), win_rate.

Data loaded from six CSVs in `data/kaggle/` (5 match files + `fifa_data.csv`); env `BRAZILIAN_SOCCER_DATA` overrides the directory.
