# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Purpose | Required args | Handler |
|------|---------|---------------|---------|
| search_matches | Find matches by team/opponent/venue/competition/season/round/date range | — | `Tools.swift:call` |
| head_to_head | H2H record + match list between two teams | team_a, team_b | `Tools.swift:call` |
| team_record | W/D/L + goals for a team, filterable by season/competition/venue | team | `Tools.swift:call` |
| standings | League table computed from match results | season | `Tools.swift:call` |
| competition_stats | Aggregate stats: goals/match, home/away/draw rates, top-scoring team | — | `Tools.swift:call` |
| biggest_wins | Largest victory margins | — | `Tools.swift:call` |
| best_records | Teams with best home/away win rate | — | `Tools.swift:call` |
| team_competitions | Which competitions/seasons a team appears in | team | `Tools.swift:call` |
| derbies | Matches between traditional rivals | — | `Tools.swift:call` |
| finals | Copa do Brasil / Libertadores finals | — | `Tools.swift:call` |
| search_players | FIFA player search by name/nationality/club/position/min rating | — | `Tools.swift:call` |
| nationality_clubs | Clubs with most players of a nationality + avg rating | — | `Tools.swift:call` |
| team_profile | Cross-dataset profile: match record + FIFA players at club | team | `Tools.swift:call` |

## JSON-RPC methods

| Method | Returns |
|--------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo |
| ping | `{}` |
| tools/list | array of 13 tool definitions (name, description, inputSchema) |
| tools/call | `{content:[{type:text,text}], isError}` |
| (unknown) | JSON-RPC error -32601; parse errors -32700 |

## Data schema (in-memory)

- `Match`: date?, homeTeam, awayTeam, homeGoals, awayGoals, competition, season, round?, stadium?, source
- `Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber, height, weight, value, skills[String:Int]
- `Competition` enum: Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C

## Data sources (data/kaggle/)

6 CSVs loaded: novo_campeonato_brasileiro.csv, Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv (matches); fifa_data.csv (18,207 players). Overlapping Brasileirão seasons de-duplicated to one source per season for clean standings.
