# Interfaces

## HTTP routes

(none) — this is not an HTTP server. It speaks the Model Context Protocol over
stdio.

## MCP transport (JSON-RPC 2.0 over newline-delimited stdio)

| Method | Result | Handler |
|--------|--------|---------|
| `initialize` | protocolVersion (negotiated from `2024-11-05`/`2025-03-26`/`2025-06-18`), capabilities, serverInfo, instructions | `mcp.go:HandleMessage` |
| `ping` | `{}` | `mcp.go:HandleMessage` |
| `tools/list` | array of `{name, description, inputSchema}` | `mcp.go:HandleMessage` |
| `tools/call` | `{content:[{type:"text",text}], isError}` | `mcp.go:HandleMessage` → `CallTool` |
| `resources/list` | `{resources:[]}` (empty) | `mcp.go:HandleMessage` |
| `prompts/list` | `{prompts:[]}` (empty) | `mcp.go:HandleMessage` |

Notifications (no `id`) get no response. Server info: name
`brazilian-soccer-mcp`, version `1.0.0`.

## CLI

| Invocation | Behaviour |
|------------|-----------|
| `brsoccer-mcp [-data DIR]` | Serve MCP over stdio |
| `brsoccer-mcp [-data DIR] -call TOOL -args JSON` | Run a single tool, print text result, exit |

Flags: `-data` (CSV directory; also `$BRSOCCER_DATA_DIR`, else `data/kaggle`),
`-call` (tool name), `-args` (JSON object of tool arguments, default `{}`).

## MCP tools (15)

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches; head-to-head when opponent given | team, opponent, venue, competition, season, date_from/to, stage, limit |
| `head_to_head` | Two-team comparison: wins, goals, per-competition, biggest win, recent | team_a*, team_b*, competition, season, limit |
| `team_stats` | W/D/L record, home/away split, per-competition, corner/shot averages | team*, venue, competition, season |
| `team_profile` | Cross-file overview: competitions, record, rivals, recent, FIFA squad | team* |
| `standings` | League table from results (3 pts/win), champion + relegation | season*, competition, limit |
| `competition_bracket` | Knockout stages of Libertadores / Copa do Brasil, final winner | competition*, season*, include_all_rounds |
| `competition_stats` | Aggregate: matches, avg goals, home/draw/away rates, corners | competition, season, team |
| `compare_seasons` | Two seasons side by side | season_a*, season_b*, competition |
| `team_rankings` | Rank teams by a metric | metric, venue, competition, season, min_matches, limit |
| `biggest_wins` | Largest margins of victory | team, competition, season, limit |
| `derbies` | Matches between traditional rivals | season, team, competition, limit |
| `search_players` | FIFA player search sorted by overall | name, nationality, club, position, min_overall, max_age, brazilian_clubs_only, limit |
| `player_details` | Full player profile; candidate list when ambiguous | name, id |
| `players_by_club` | Group players by club (size, avg rating, best) | nationality, brazilian_clubs_only, limit |
| `dataset_info` | Coverage: rows per CSV, competitions/season ranges, team & player counts | (none) |

(* = required argument.) Ranking metrics: `win_rate`, `points_per_game`,
`points`, `wins`, `goals_for`, `goals_against`, `goal_difference`.

## Data schema (in-memory, loaded from CSV)

**Match**: Date, Competition, Season, Round, Stage, HomeKey, AwayKey, HomeGoals,
AwayGoals, Arena, Ext (`*ExtStats`: corners/attacks/shots), Sources.

**Player**: ID, Name, Age, Nationality, Overall, Potential, Club, ClubKey,
Position, Jersey, Height, Weight, Foot, Value, Wage, Skills (35 skill columns).

**Team** (canonical): Key (`base|state`), Base, State, Name, Matches.

Source CSVs: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`,
`novo_campeonato_brasileiro.csv`, `fifa_data.csv`. Competitions:
Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.
