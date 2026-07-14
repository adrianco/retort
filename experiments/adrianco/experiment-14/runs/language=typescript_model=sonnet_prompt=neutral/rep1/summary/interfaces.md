# Interfaces

## MCP tools

| Tool | Required args | Returns | Handler |
|------|---------------|---------|---------|
| `search_matches` | — | Matches by team/home_team/away_team/season/date range/competition | `index.ts` → `queryMatches` |
| `get_team_stats` | `team` | W/L/D record, points, goals for/against, home/away splits | `index.ts` → `getTeamStats` |
| `get_head_to_head` | `team1`, `team2` | H2H wins/draws/goals + recent matches | `index.ts` → `getHeadToHead` |
| `get_standings` | `season` | League table computed from matches | `index.ts` → `getStandings` |
| `search_players` | — | FIFA players by name/nationality/club/position/min_overall | `index.ts` → `queryPlayers` |
| `get_biggest_wins` | — | Largest goal-difference matches | `index.ts` → `getBiggestWins` |
| `get_league_stats` | — | Total matches/goals, avg goals/match, home win rate | `index.ts` → `getLeagueStats` |
| `get_top_scoring_teams` | — | Teams ranked by goals scored | `index.ts` → `getTopScoringTeams` |
| `get_dataset_info` | — | Dataset coverage counts + tool listing | `index.ts` (inline) |

Transport: `StdioServerTransport` (MCP over stdio).

## Data schema (`DataStore`)

In-memory arrays parsed from `data/kaggle/`:
- `brasileirao` (Brasileirao_Matches.csv, 2012–2022), `copa` (Brazilian_Cup_Matches.csv), `libertadores` (Libertadores_Matches.csv), `extended` (BR-Football-Dataset.csv), `historical` (novo_campeonato_brasileiro.csv, 2003–2019), `players` (fifa_data.csv).
- Matches normalized into a `UnifiedMatch` (`competition`, `date`, `home_team`, `away_team`, `home_goal`, `away_goal`, `season`, `extra`).
- Team names normalized via `normalizeTeamName` (strips `-SP`/`-RJ` state suffixes and parentheticals).

## HTTP routes / CLI commands

(none)
