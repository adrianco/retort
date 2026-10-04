# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behaviour |
|--------|-----------|
| `initialize` | Negotiates protocolVersion (2025-06-18 / 2025-03-26 / 2024-11-05), advertises `tools` capability + serverInfo |
| `ping` | Returns `{}` |
| `tools/list` | Returns the 17 tool definitions with JSON input schemas |
| `tools/call` | Runs a tool; result is `{content:[{type:"text",text}], isError}` (tool errors reported in-band) |
| `resources/list`, `prompts/list` | Return empty arrays |
| notifications (`notifications/initialized`, …) | No reply |
| batch (JSON array) | Handled element-wise |

Errors use standard JSON-RPC codes: -32700 parse, -32600 invalid request, -32601 method not found, -32602 invalid params.

## Tools (17)

| Tool | Purpose | Required args |
|------|---------|---------------|
| `find_matches` | Matches by team/opponent/venue/competition/season/date range/stage, ordered | — |
| `head_to_head` | H2H record + recent meetings between two teams | team_a, team_b |
| `team_stats` | W/D/L, goals for/against, win rate, home/away + per-competition split | team |
| `team_competitions` | Competitions/seasons a team appears in, with record | team |
| `team_profile` | Cross-dataset: match record + FIFA squad | team |
| `standings` | League table computed from results (3pts/win), champion/relegation | season |
| `competition_bracket` | Knockout results (Libertadores by stage, Copa do Brasil by round) | season |
| `league_stats` | Aggregate: goals/match, home/draw/away rates, most goals | — |
| `biggest_wins` | Largest margins, filterable | — |
| `team_rankings` | Rank teams by win_rate/points/ppg/goals_for/against/GD | — |
| `compare_seasons` | Two-season comparison of a competition | season_a, season_b |
| `derbies` | Traditional rivalry matches | — |
| `search_players` | FIFA search by name/nationality/club/position/min_overall | — |
| `player_details` | Full FIFA profile + club match record | name |
| `club_player_summary` | Players of a nationality grouped by club | — |
| `dataset_info` | Loaded datasets, rows/file, competitions, coverage | — |

## CLI

`brazilian-soccer-mcp [--data DIR]` serve over stdio · `--list-tools` · `--call TOOL [JSON_ARGS]` run one tool. Data dir resolves from `--data`, `$BRSOCCER_DATA_DIR`, `./data/kaggle`, then paths near the executable.

## Data schema (in-memory)

- **BSMatch**: date, time, homeKey/awayKey, competition, round, stage, arena, source, season, home/awayGoals, hasScore, extra (shots/corners/attacks).
- **BSPlayer**: playerID, name, nationality, club, position, foldedName/Club, clubKey, age, overall, potential, raw row.

Source: six CSVs in `data/kaggle/` (Brasileirao, Brazilian_Cup, Libertadores, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data).
