# Interfaces

## MCP (JSON-RPC 2.0 over stdio)

Methods dispatched by `server.ex:dispatch/3`:

| Method | Returns | Notes |
|--------|---------|-------|
| `initialize` | protocolVersion `2024-11-05`, capabilities `{tools:{}}`, serverInfo | |
| `ping` | `{}` | |
| `tools/list` | `{tools: [...]}` | 8 tool descriptors |
| `tools/call` | `{content:[{type:"text",text}], isError}` | tool errors returned as results, not JSON-RPC errors |

Notifications (no `id`) get no response. Protocol errors use JSON-RPC error codes (`-32700`/`-32600`/`-32601`/`-32602`).

## MCP tools (`tools.ex:list/0`)

| Tool | Purpose | Required args |
|------|---------|---------------|
| `search_matches` | Matches by team/side/opponent/derby/competition/season/date range | (none) |
| `team_record` | W/D/L record, goals, win rate for one team | `team` |
| `head_to_head` | Head-to-head record + recent meetings between two teams | `team_a`, `team_b` |
| `standings` | League table from results (3-1-0) | `season` |
| `league_stats` | Aggregate: matches, goals/match, home/away/draw rates | (none) |
| `biggest_wins` | Largest winning margins | (none) |
| `team_ranking` | Rank teams by `home_win_rate`/`away_win_rate`/`win_rate`/`wins`/`points`/`goals_for` | `metric` |
| `search_players` | FIFA players by name/nationality/club/position/min rating | (none) |

## CLI

`brazilian_soccer [--data-dir data/kaggle] [--help]` (via escript) or
`mix run -e 'BrazilianSoccer.CLI.main(["--data-dir","data/kaggle"])'`.

## Data schema (loaded structs)

- `Match`: date (`Date`), competition, stage, home/away (+ normalized `home_key`/`away_key`), home_goals, away_goals, source.
- `Player`: id, name, age, nationality, club, position, overall, potential, jersey_number, value, wage.

## Datasets consumed

`data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv` (5 match files, merged + de-duplicated), `fifa_data.csv` (players).
