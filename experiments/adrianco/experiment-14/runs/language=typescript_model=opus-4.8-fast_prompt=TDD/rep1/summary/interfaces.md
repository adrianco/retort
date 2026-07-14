# Interfaces

## MCP tools

Registered in `tools.ts:createTools` and wired into the server in `server.ts:buildServer`. Each returns a single formatted text content block.

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `find_matches` | team?, team2?, homeTeam?, awayTeam?, competition?, season?, from?, to?, limit? | match list (+ head-to-head when two teams) | `tools.ts:findMatches` |
| `team_record` | team, season?, competition?, venue? | W/D/L, goals, points | `tools.ts:teamRecord` |
| `head_to_head` | teamA, teamB, limit? | meetings, per-side wins, draws, match list | `tools.ts:headToHead` |
| `standings` | competition, season | computed points table | `tools.ts:standings` |
| `match_statistics` | competition?, season?, team? | avg goals, home/away/draw rates | `tools.ts:matchStatistics` |
| `biggest_wins` | competition?, season?, team?, limit? | matches by goal margin | `tools.ts:biggestWins` |
| `search_players` | name?, nationality?, club?, position?, minOverall?, limit? | FIFA players sorted by overall | `tools.ts:searchPlayers` |
| `brazilian_players_by_club` | limit? | per-club counts + avg rating | `tools.ts:brazilianByClub` |

## Library API

`SoccerDatabase` (database.ts) exposes: `findMatches`, `headToHead`, `teamRecord`, `standings`, `statistics`, `biggestWins`, `findPlayers`, `brazilianPlayersByClub`.

## Data schema

- **Match**: competition, date, season, round?, stage?, homeTeam/awayTeam (+ normalized keys), homeGoals, awayGoals, arena?, source, stats?.
- **Player**: id, name (+ key), age, nationality, overall, potential, club (+ key), position, jerseyNumber, height, weight.

## Data sources

Six bundled Kaggle CSVs in `data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches), `fifa_data.csv` (players). Data dir overridable via `BRAZILIAN_SOCCER_DATA_DIR`.
