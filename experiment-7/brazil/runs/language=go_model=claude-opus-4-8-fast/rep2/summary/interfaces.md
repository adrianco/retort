# Interfaces

## MCP tools (transport: JSON-RPC 2.0 over stdio)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| find_matches | team, opponent, competition, season, start_date, end_date, home_away, limit | Match list (+ head-to-head when team+opponent) | `tools.go:handleFindMatches` |
| team_stats | team* , season, competition, home_away | W/D/L, goals, points, win rate | `tools.go:handleTeamStats` |
| head_to_head | team1* , team2* , limit | Head-to-head W/D/L, goals, recent meetings | `tools.go:handleHeadToHead` |
| search_players | name, nationality, club, position, min_overall, limit | Player list sorted by rating | `tools.go:handleSearchPlayers` |
| standings | season* , competition, limit | Computed league table | `tools.go:handleStandings` |
| competition_stats | competition, season | Avg goals, home/away/draw rates, biggest wins | `tools.go:handleCompetitionStats` |
| list_competitions | (none) | Competitions + season ranges, totals loaded | `tools.go:handleListCompetitions` |

\* = required argument (enforced via JSON Schema `required` and/or handler validation).

## JSON-RPC methods

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`. Protocol version `2024-11-05`.

## Data schema (in-memory)

- **Match**: date, home/away team (display + canonical keys + base keys + state), goals, season, round, competition, stage, stadium, source, optional shots/corners.
- **Player**: id, name (+ key), age, nationality, overall, potential, club (+ key), position, jersey, height, weight, preferred foot.

## Data sources

Six bundled Kaggle CSVs under `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, novo_campeonato_brasileiro, BR-Football-Dataset (matches) + fifa_data (players).
