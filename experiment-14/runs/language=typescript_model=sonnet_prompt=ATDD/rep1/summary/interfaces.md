# Interfaces

## MCP tools (transport: stdio)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| `find_matches` | team?, competition?, season?, limit? | `[Match]` (JSON text) | `tools/matches.ts:findMatches` |
| `get_team_stats` | **team**, competition?, season? | `{team, wins, losses, draws, goals_scored, goals_conceded, points, ...}` | `tools/teams.ts:getTeamStats` |
| `find_players` | name?, nationality?, club?, minRating?, position?, limit? | `[Player]` | `tools/players.ts:findPlayers` |
| `get_head_to_head` | **team1**, **team2**, competition?, season? | `{total_matches, team1_wins, team2_wins, draws, matches}` | `tools/headToHead.ts:getHeadToHead` |
| `get_standings` | **competition**, **season** | `[{position, team, played, won, drawn, lost, gf, ga, gd, points}]` | `tools/standings.ts:getStandings` |

Bold = required argument. All tool results are returned as a single `text` content block containing `JSON.stringify(result)`; on error the handler returns `{error}` with `isError: true`.

## Data schema (CSV inputs, `data/kaggle/`)

| File | Used by | Key columns |
|------|---------|-------------|
| Brasileirao_Matches.csv | matches, teams, h2h, standings | home_team, away_team, home_goal, away_goal, season |
| Brazilian_Cup_Matches.csv | matches, teams, h2h | home_team, away_team, home_goal, away_goal, season |
| Libertadores_Matches.csv | matches, teams, h2h | home_team, away_team, home_goal, away_goal, season |
| BR-Football-Dataset.csv | matches | home, away, home_goal, away_goal, date |
| novo_campeonato_brasileiro.csv | matches, h2h, standings | Equipe_mandante, Equipe_visitante, Gols_mandante, Gols_visitante, Ano |
| fifa_data.csv | players | ID, Name, Nationality, Club, Overall, Position |
| brazilian_clubs_players.csv | players (supplement) | ID, Name, Nationality, Club, Overall |

## HTTP routes / CLI commands

(none) — surface is the MCP tool protocol only.
