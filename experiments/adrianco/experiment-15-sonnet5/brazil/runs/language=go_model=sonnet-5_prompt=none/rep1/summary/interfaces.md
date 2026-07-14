# Interfaces

## MCP transport

Newline-delimited JSON-RPC 2.0 over stdio (protocol version `2024-11-05`).
Methods handled: `initialize`, `notifications/initialized`, `notifications/cancelled`,
`ping`, `tools/list`, `tools/call`. Unknown methods return JSON-RPC error `-32601`.

## MCP tools

| Tool | Required args | Optional args | Returns | Handler |
|------|---------------|---------------|---------|---------|
| `search_matches` | — | team, opponent, competition, season, date_from, date_to, limit | matches (recent-first) + optional H2H summary | `queries.go:SearchMatches` |
| `head_to_head` | team_a, team_b | competition, season, limit | W/D/L, goals, biggest wins, recent matches | `queries.go:HeadToHead` |
| `team_record` | team | season, competition, venue | played/W/D/L, goals for/against, win-rate, competitions, top squad players | `queries.go:TeamRecord` |
| `standings` | season | competition (default Brasileirão) | league table (points 3/1/0, GD), champion | `queries.go:Standings` |
| `stats_overview` | — | competition, season | avg goals/match, home/away/draw rates, biggest wins, best home/away teams | `queries.go:StatsOverview` |
| `search_players` | — | name, nationality, club, position, min_overall, limit | FIFA players sorted by overall rating | `queries.go:SearchPlayers` |

## Data sources (data/kaggle/)

| File | Mapped competition | Notes |
|------|--------------------|-------|
| Brasileirao_Matches.csv | Brasileirão | Serie A, primary source |
| novo_campeonato_brasileiro.csv | Brasileirão | older seasons only (dedup vs primary) |
| Brazilian_Cup_Matches.csv | Copa do Brasil | |
| Libertadores_Matches.csv | Copa Libertadores | NA seasons skipped |
| BR-Football-Dataset.csv | `<tournament> (Extended Stats)` | corners/shots/attacks; overlap seasons skipped |
| fifa_data.csv | — | Player records (BOM-stripped) |

## Data schema

`Match`: competition, season, round/stage, date, home/away team+state, home/away goals, arena, source, optional extended stats.
`Player`: id, name, age, nationality, overall, potential, club, position, jersey, height, weight, value, wage.
