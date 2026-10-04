# Interfaces

## MCP tools (registered in `src/server.ts`)

| Tool | Purpose | Handler |
|------|---------|---------|
| search_matches | Matches by team/opponent/venue/season/competition/stage/date range | `queries.ts:searchMatches` |
| last_meeting | Most recent match between two teams, with score | `queries.ts:lastMeeting` |
| head_to_head | Head-to-head record across all competitions | `queries.ts:headToHead` |
| team_record | W/D/L and goals, by season/venue/competition | `queries.ts:teamRecord` |
| team_competitions | Competitions a team has played in | `queries.ts:teamCompetitions` |
| standings | Brasileirão league table computed from matches | `queries.ts:standings` |
| top_scoring_teams | Teams with most goals (optional season) | `queries.ts:topScoringTeams` |
| competition_stats | Avg goals/match, home/draw/away rates | `queries.ts:competitionStats` |
| compare_seasons | Aggregate stats across seasons | `queries.ts:compareSeasons` |
| biggest_wins | Largest margins of victory | `queries.ts:biggestWins` |
| best_record | Rank teams by home/away/overall win rate | `queries.ts:bestRecord` |
| derbies | Matches between traditional rivals | `queries.ts:derbies` |
| search_players | FIFA players by name/nationality/club/position/rating | `queries.ts:searchPlayers` |
| dataset_info | Describe loaded datasets | `queries.ts:datasetInfo` |

## Data schema (in-memory, `src/data.ts`)

- `Match`: date, time?, season, competition, round?, stage?, home, away, homeGoals, awayGoals, arena?, source, stats?
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey, height, weight, foot, value, skills{}
- `Dataset`: matches[], players[], files{}, league[] (preferred-source rows per season), seasonSources(Map)

## Data sources

6 CSVs under `data/kaggle/`: Brasileirao_Matches, novo_campeonato_brasileiro, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, fifa_data.
