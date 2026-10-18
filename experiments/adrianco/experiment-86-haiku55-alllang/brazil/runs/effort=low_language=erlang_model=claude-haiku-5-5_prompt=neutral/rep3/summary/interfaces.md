# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

Newline-delimited JSON-RPC 2.0 on stdin/stdout (`bs_mcp.erl`). stdout carries protocol messages only; diagnostics go to stderr.

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | `protocolVersion` 2024-11-05, `capabilities.tools`, `serverInfo` | `bs_mcp.erl:52` |
| `ping` | `{}` | `bs_mcp.erl:56` |
| `tools/list` | `{tools: [...]}` — 7 tool schemas | `bs_mcp.erl:58` |
| `tools/call` | `{content: [{type:text,...}], isError}` | `bs_mcp.erl:60` |

Notifications (no `id`) are accepted and never answered. Parse errors → `-32700`; invalid request → `-32600`; unknown method → `-32601`. Tool failures are returned as results with `isError:true` so the model can retry.

## MCP tools (`bs_tools:list/0`)

| Tool | Purpose | Arguments (required) |
|------|---------|----------------------|
| `search_matches` | Find matches by team/opponent/competition/season/date range | team, opponent, competition, season, from, to, limit |
| `team_stats` | W/D/L, goals, win rate with home/away splits | **team**, season, competition, from, to |
| `head_to_head` | Record between two teams across the dataset | **team1**, **team2**, limit |
| `standings` | League table computed from match results (3/1/0 pts) | **season**, competition |
| `aggregate_stats` | average_goals \| home_win_rate \| biggest_wins \| best_away_record \| top_scorers | **metric**, season, competition, team, from, to |
| `search_players` | Search FIFA players by name/nationality/club/position/rating | name, nationality, club, position, min_overall, limit |
| `brazilian_club_summary` | Brazilian players grouped by Brazilian club | (none) |

## Data schema

- **match()** (`bs_data.erl:17`): date, season, competition, round, home, away, home_name, away_name, home_goals, away_goals, source.
- **player()** (`bs_data.erl:22`): id, name, name_key, age, nationality, overall, potential, club, club_key, position, value, wage, preferred_foot, height, weight, jersey.

## CLI

`brazilian_soccer_mcp [DataDir]` — escript entry (`brazilian_soccer_mcp.erl:11`). DataDir defaults to `$BS_DATA_DIR`, then `data/kaggle`.

## Data sources loaded (`bs_data.erl:32`)

`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, and `fifa_data.csv`.
