# Interfaces

## MCP transport

JSON-RPC 2.0 over line-delimited stdin/stdout. Supported methods: `initialize`,
`ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`,
`notifications/*`. Protocol versions negotiated: `2025-06-18`, `2025-03-26`,
`2024-11-05`. Defined in `internal/mcpserver/server.go:dispatch`.

## MCP tools (20)

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Find matches by team/opponent/venue/competition/season/date/stage | `tools.go:searchMatches` |
| last_meeting | Most recent meeting of two teams + score | `tools.go:lastMeeting` |
| head_to_head | Two-team H2H: meetings, W/D/L, goals, per-competition | `tools.go:headToHead` |
| find_derbies | Matches between traditional rivals | `tools.go:findDerbies` |
| team_record | W/D/L, goals for/against, points, win rate, by competition | `tools.go:teamRecord` |
| rank_teams | Rank teams by win_rate/points/goals/… with filters | `tools.go:rankTeams` |
| team_competitions | Which competitions a team has played in | `tools.go:teamCompetitions` |
| find_team | Resolve a name to a team and list spellings | `tools.go:findTeam` |
| club_profile | Squad (FIFA) + results (matches) for a club | `tools.go:clubProfile` |
| standings | League table for a Brasileirão season, champion + relegated | `tools.go:standings` |
| knockout_bracket | Knockout ties stage-by-stage with aggregates | `tools.go:bracket` |
| search_players | Players by name/nationality/club/position/rating/age | `tools.go:searchPlayers` |
| get_player | Player profile: club, nationality, ratings, attributes | `tools.go:getPlayer` |
| brazilian_players_by_club | Count of a nationality per Brazilian club + avg rating | `tools.go:playersByClub` |
| competition_stats | Avg goals/match, home/draw/away rates, corners, shots | `tools.go:competitionStats` |
| biggest_wins | Most one-sided results by margin | `tools.go:biggestWins` |
| compare_seasons | Compare seasons: goals, results split, champion, top scorer | `tools.go:compareSeasons` |
| dataset_overview | What datasets are loaded, records, seasons | `tools.go:overview` |

(The table lists 18 named handlers; `search_matches` and `find_derbies` share
the underlying search, and `team_record`/`rank_teams` cover the two aggregate
views — 20 `Tool` entries total as registered in `tools()`.)

## Data schema (in-memory)

- **Match**: Date, Competition, Season, Round, Stage, HomeKey, AwayKey,
  HomeGoals, AwayGoals, Arena, optional MatchStats (corners/shots/attacks),
  Sources.
- **Player**: ID, Name, Age, Nationality, Overall, Potential, Club/ClubKey,
  Position, Jersey, Height, Weight, Value, Wage, foot, contract, Skills[].
- **Team**: Key, Display, Known, Variants (spelling → count).
- **Dataset**: Name, File, Records, NewMatches, Merged, Skipped, Seasons, Error.

Source data: six CSVs under `data/kaggle/` (5 match files + FIFA players),
loaded once at startup.
