# Interfaces

## MCP tools

Registered via `@modelcontextprotocol/sdk` in `src/server.ts:createServer`, served over stdio.

| Tool | Purpose | Key inputs | Handler |
|------|---------|-----------|---------|
| `find_matches` | Find matches by team/competition/season/date range | team, homeTeam, awayTeam, competition, season, from, to, limit | `queries/matches.ts:findMatches` |
| `head_to_head` | Head-to-head W/D/L between two teams | teamA, teamB, competition?, season? | `queries/matches.ts:headToHead` |
| `last_meeting` | Most recent match between two teams | teamA, teamB | `queries/matches.ts:lastMeeting` |
| `team_record` | W/D/L, goals, home/away split for a team | team, competition?, season? | `queries/teams.ts:teamStats` |
| `search_players` | Search FIFA players by name/nationality/club/position/rating | name?, nationality?, club?, position?, minOverall?, limit? | `queries/players.ts:filterPlayers` + `rankByOverall` |
| `players_by_club_summary` | Group players by club with counts/avg ratings | nationality?, club?, limit? | `queries/players.ts:summarizeByClub` |
| `league_standings` | Brasileirão season table calculated from matches | season, limit? | `queries/competitions.ts:brasileiraoStandings` |
| `competition_champion` | Brasileirão champion for a season | season | `queries/competitions.ts:brasileiraoChampion` |
| `aggregate_stats` | Avg goals/match, home/away win rates | competition?, season?, team? | `queries/stats.ts:aggregateStats` |
| `biggest_wins` | Matches with largest goal margins | competition?, season?, team?, limit? | `queries/stats.ts:biggestWins` |
| `top_scoring_teams` | Rank teams by total goals scored | competition?, season?, limit? | `queries/stats.ts:topScoringTeams` |

## Library API

Exported query functions (see modules.md) are directly callable and independently unit-tested, decoupled from the MCP transport.

## Data schema (in-memory)

- `Match`: competition, source, date, season, round, stage, homeTeam/awayTeam (+ raw), homeGoals/awayGoals.
- `Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber, height, weight, preferredFoot, value, wage.

## Data sources

Six CSVs in `data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches), `fifa_data.csv` (players). Data dir overridable via `SOCCER_DATA_DIR`.
