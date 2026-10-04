# Interfaces

## MCP tools (17)

Exposed over MCP `tools/call` and via `brazilian-soccer-mcp call <tool> <json>`.

| Tool | Purpose | Required args |
|------|---------|---------------|
| search_matches | Matches by team/opponent/venue/competition/season/date/stage | (none) |
| head_to_head | H2H record + match list between two teams | team_a, team_b |
| team_stats | W/D/L, goals for/against, win rate, per-competition breakdown | team |
| team_profile | Cross-dataset team profile incl. FIFA squad | team |
| standings | League table computed from matches, champion/relegation | season |
| competition_summary | Season summary; knockout bracket by stage | competition, season |
| league_stats | Aggregate goals/match, home/draw/away rates, top match | (none) |
| biggest_wins | Largest winning margins | (none) |
| team_rankings | Rank teams by win_rate/points/goals/etc. | (none) |
| compare_seasons | Compare two seasons of a competition | season_a, season_b |
| derbies | Matches between traditional rivals | (none) |
| search_players | FIFA players by name/nationality/club/position | (none) |
| player_details | Full profile of one player | name |
| brazilian_clubs_players | Player count/avg rating per Brazilian club | (none) |
| list_teams | List team names in match data | (none) |
| dataset_info | Files, row counts, competitions/seasons covered | (none) |

## JSON-RPC methods

`initialize`, `ping`, `tools/list`, `tools/call`. Unknown method → -32601; bad params → -32602; parse error → -32700; invalid request → -32600.

## CLI commands

| Command | Effect |
|---------|--------|
| `brazilian-soccer-mcp [--data-dir DIR]` | Serve MCP on stdio |
| `brazilian-soccer-mcp call TOOL [JSON]` | Run one tool, print text answer |
| `brazilian-soccer-mcp tools` | List tool names + descriptions |

## Library API

`Database::load(&Path) -> Result<Database, String>`; query methods on `Database` (see modules.md); `mcp::call_tool`, `mcp::handle_message`, `mcp::serve`, `mcp::tool_definitions`.

## Data schema (in-memory)

`Match`: date, season, competition, source, round/stage, home/away (+keys), home_goal/away_goal (Option), arena, extra (corners/shots/attacks), primary flag.
`Player`: id, name, age, nationality, overall/potential, club (+key), position, jersey, height/weight/value/wage/foot, skills.
Loaded from 6 CSVs in `data/kaggle/`; overlapping league seasons de-duplicated to one primary source.
