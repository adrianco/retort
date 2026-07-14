# Interfaces

## MCP tools (JSON-RPC over stdio)

The server speaks MCP: `initialize`, `tools/list`, `tools/call`, `ping`. Nine tools
are registered (`McpServer.java:handleToolsList`) and dispatched in
`handleToolCall`:

| Tool | Params | Handler |
|------|--------|---------|
| search_matches | team, team2, competition, season, start_date, end_date, limit | `MatchTools.searchMatches` |
| head_to_head | team1, team2, competition, season | `MatchTools.headToHead` |
| team_stats | team, season, competition | `MatchTools.teamStats` |
| standings | competition, season | `MatchTools.standings` |
| match_statistics | competition, season, stat_type (biggest_wins/goals_avg/home_away) | `MatchTools.matchStatistics` |
| search_players | name, nationality, club, position, min_overall, sort_by, max_results | `PlayerTools.searchPlayers` |
| player_profile | name | `PlayerTools.playerProfile` |
| team_players | club, min_overall, sort_by | `PlayerTools.teamPlayers` |
| top_players_by_nationality | nationality, limit | `PlayerTools.topPlayersByNationality` |

## Data schema (in-memory)

- **Match**: datetime, homeTeam, awayTeam, homeGoals, awayGoals, season, round,
  competition, stage, homeState, awayState, arena, winner, corners/shots (nullable).
- **Player**: id, name, age, nationality, overall, potential, club, position,
  jerseyNumber, physicals, dribbling/shooting/passing/defending/pace.

## Data sources (CSV, `data/kaggle/`)

All 6 loaded: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`,
`novo_campeonato_brasileiro.csv`, `fifa_data.csv`.

## HTTP routes / CLI commands

(none — transport is MCP stdio JSON-RPC, not HTTP or a flag-based CLI.)
