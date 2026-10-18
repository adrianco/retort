# Interfaces

## MCP tools (`tools/call`)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| search_matches | team, opponent, competition, season, from, to, venue, limit | text list of fixtures | `SoccerTools:searchMatches` → `SoccerQueries.findMatches` |
| team_record | team*, season, competition, venue | W/D/L, goals, win rate | `SoccerTools:teamRecord` → `SoccerQueries.teamRecord` |
| head_to_head | team_a*, team_b*, limit | all-time H2H W/D/L + recent matches | `SoccerTools:headToHead` → `SoccerQueries.headToHead` |
| search_players | name, nationality, club, position, min_overall, limit | ranked player list with ratings | `SoccerTools:searchPlayers` → `SoccerQueries.searchPlayers` |
| competition_standings | season*, competition | league table from results | `SoccerTools:standings` → `SoccerQueries.standings` |
| league_stats | competition, season | avg goals, home/draw/away rates, biggest wins | `SoccerTools:leagueStats` → `SoccerQueries.leagueStats` |
| rank_teams | competition, season, venue, min_matches, limit | teams ranked by win rate | `SoccerTools:rankTeams` → `SoccerQueries.rankTeams` |

(* = required argument.) Transport is newline-delimited JSON-RPC 2.0 on stdio; lifecycle methods `initialize`, `notifications/initialized`, `ping`, `tools/list` are also handled.

## Data schema (in-memory records)

- `Match`: date (LocalDate), competition (String), round (String), homeTeam, awayTeam, homeGoals (Integer|null), awayGoals (Integer|null); derived `season()`, `hasResult()`.
- `Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber.

## Data sources loaded (`data/kaggle/`)

Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv (matches); fifa_data.csv (players). Match sources are merged and de-duplicated within a 3-day window.

## CLI

`Main` takes an optional data-directory argument (else `$SOCCER_DATA_DIR`, else `data/kaggle`). No other CLI subcommands.
