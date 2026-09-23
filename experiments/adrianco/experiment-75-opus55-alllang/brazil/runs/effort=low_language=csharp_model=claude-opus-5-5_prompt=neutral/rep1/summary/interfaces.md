# Interfaces

## MCP transport

JSON-RPC 2.0 over newline-delimited stdio (`McpServer.RunAsync`). Methods handled:
`initialize`, `ping`, `tools/list`, `tools/call`. Notifications (no `id`) return no
response. Unknown method → `-32601`; parse error → `-32700`; handler exception → `-32603`.

## MCP tools (`tools/call`)

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Find matches by team/opponent/competition/season/date range/venue/round | `Tools.SearchMatches` |
| head_to_head | Head-to-head record + matches between two teams | `Tools.HeadToHeadTool` |
| team_stats | W/D/L record and goals for a team (by season/competition/venue) | `Tools.TeamStats` |
| team_competitions | Competitions a team has played in | `Tools.All` inline lambda |
| standings | League table for a season computed from results | `Tools.Standings` |
| top_scoring_teams | Teams ranked by goals scored in a season | `Tools.TopScoring` |
| biggest_wins | Largest-margin victories | `Tools.BiggestWins` |
| competition_stats | Avg goals/match, home/away/draw rates | `Tools.CompStats` |
| compare_seasons | Aggregate + champion comparison of two seasons | `Tools.CompareSeasons` |
| best_records | Teams by win rate (home/away/overall) | `Tools.BestRecords` |
| derbies | Traditional rivalry matches | `Tools.DerbiesTool` |
| search_players | FIFA player search by name/nationality/club/position/min rating | `Tools.SearchPlayers` |
| player_details | Full profile + skill ratings for a player | `Tools.PlayerDetails` |
| brazilian_club_players | Players at clubs appearing in Brazilian match data (cross-file) | `Tools.ClubPlayers` |
| dataset_info | Row counts per CSV | `Tools.DatasetInfo` |

## CLI

`dotnet run -- <tool> '{json args}'` — invokes one tool handler and prints its text (Program.cs).

## Data schema (in-memory)

- `Match(Date, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Competition, Season, Round, Source, Arena?, HomeCorners?, AwayCorners?, HomeShots?, AwayShots?)` with derived `HomeKey`, `AwayKey`, `Margin`, `TotalGoals`.
- `Player(Id, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight, PreferredFoot, Value, Skills)`.

## Data sources

Loads six CSVs from `data/kaggle/` (data-dir found via `SOCCER_DATA_DIR` env or by walking up
from CWD/AppContext.BaseDirectory): Brasileirao, Copa do Brasil, Libertadores,
BR-Football-Dataset, novo_campeonato_brasileiro (historical), fifa_data (players).
