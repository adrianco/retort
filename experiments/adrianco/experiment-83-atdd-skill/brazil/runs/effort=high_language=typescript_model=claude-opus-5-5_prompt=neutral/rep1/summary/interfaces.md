# Interfaces

## MCP tools (17)

Registered in `src/server.ts` from the `TOOLS` table in `src/tools.ts`; each exposes a zod `inputSchema` and returns text content.

| Tool | Purpose | Backing query (`src/query.ts`) |
|------|---------|--------------------------------|
| search_matches | Find matches by team/opponent/venue/competition/season/date/stage | `searchMatches()` |
| head_to_head | Head-to-head W/L/D and goals between two teams | `headToHead()` |
| team_record | Aggregated W/L/D + goals for/against (home/away/by-competition) | `teamRecord()` |
| team_profile | Competitions, seasons, record, linked FIFA squad, rivals | `teamProfile()` |
| standings | League table computed from match results (CBF tie-breakers) | `standings()` |
| cup_bracket | Knockout ties by stage with inferred winners | `bracket()` |
| cup_finals | All finals of a cup across seasons | `finals()` |
| match_statistics | Aggregate stats: avg goals, home/away/draw rates, scorelines | `matchStats()` |
| biggest_wins | Largest victory margins (optionally per team) | `biggestWins()` |
| team_rankings | Rank teams by a metric (points, win-rate, goals, clean sheets, ...) | `teamRankings()` |
| compare_seasons | Season-by-season comparison with champion + top scorer | `compareSeasons()` |
| derbies | Matches between traditional rivals | `derbies()` |
| search_players | Filter players by name/nationality/club/position/rating/age | `searchPlayers()` |
| get_player | Single-player lookup with alternatives/suggestions | `getPlayer()` |
| club_player_summary | Player counts & avg rating grouped by club | `clubSummary()` |
| find_team | Resolve free-text team name to canonical team(s) | `findTeams()` |
| dataset_info | Loaded-row counts and source-file provenance | dataset metadata |

## Data schema (in-memory)

- **Match**: id, competition (`serie-a`/`serie-b`/`serie-c`/`copa-do-brasil`/`libertadores`), season, date, time?, round?, stage?, homeId, awayId, homeGoals, awayGoals, arena?, stats?, sources[]
- **Player**: id, name, age, nationality, overall, potential, club, teamId?, position, jerseyNumber, height, weight, preferredFoot, value, wage, skills{}, searchName
- **Dataset**: matches[], players[], teams (TeamRegistry), sources[], brazilianClubs(Set), loadMs

## Data sources

Six Kaggle CSVs under `data/kaggle/`: `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv` (matches), `fifa_data.csv` (players). No network/API calls.

## CLI commands

(none — single stdio MCP entry point; `BRAZIL_SOCCER_DATA_DIR` env var overrides the data directory.)
