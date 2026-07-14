# Interfaces

## MCP tools (`tools/list` + `tools/call`)

Exposed over the JSON-RPC MCP stdio transport (`lib/br_soccer/mcp/server.ex`); defined in `lib/br_soccer/mcp/tools.ex`.

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Find matches by team/opponent/competition/season/date range | team, opponent, venue, competition, season, date_from, date_to, limit |
| `head_to_head` | Head-to-head record + match list between two clubs | team_a, team_b, competition, season |
| `last_match` | Most recent meeting between two clubs | team_a, team_b |
| `team_record` | W/D/L record, goals, win rate for a club | team, season, competition, venue |
| `team_competitions` | Competitions a club appeared in, with counts | team |
| `league_standings` | Final league table computed from results | competition, season |
| `relegated_teams` | Bottom-N of a 20-team Brasileirão season | season, count |
| `search_players` | FIFA players by name/nationality/club/position/rating | name, nationality, club, position, min_overall, sort, limit |
| `player_profile` | Detailed card for best name match | name |
| `brazilian_clubs_squads` | Brazilian players grouped by Brazilian club | min_count, limit |
| `competition_stats` | Avg goals/match, home/away/draw rates | competition, season |
| `biggest_wins` | Largest-margin victories in a filtered set | competition, season, team, limit |
| `top_scoring_teams` | Teams ranked by goals scored | competition, season, limit |
| `team_rankings` | Teams ranked by venue win rate | competition, season, venue, limit |
| `compare_seasons` | Two seasons side by side | competition, season_a, season_b |

## MCP protocol methods (JSON-RPC 2.0)

`initialize`, `tools/list`, `tools/call`, `ping`; `notifications/*` are accepted and ignored. Unknown methods return error `-32601`.

## CLI

`lib/br_soccer/mcp/cli.ex` (escript `main_module`):
- default: run the stdio MCP serve loop.
- `--ask <tool> key=value ...`: run a single tool call and print the result (manual check without an MCP client).

## Library API

`BrSoccer` facade (`lib/br_soccer.ex`) delegates to the query modules — `search_matches/1`, `head_to_head/3`, `team_record/2`, `team_rankings/1`, `biggest_wins/1`, `top_scoring_teams/1`, `search_players/1`, `brazilian_clubs_squads/1`, `standings/2`, `champion/2`, `relegated/2`, `stats_summary/1`, `compare_seasons/3`, `last_match/2`.

## Data sources

Six CSVs under `data/kaggle/` are parsed into in-memory structs (no DB):
- `Match`: competition, source, season, date, home/away (+ normalised keys), goals, state, arena, stats map.
- `Player`: id, name, age, nationality, overall, potential, club (+ key), position, jersey, physicals, value, wage, foot.

Match files (`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv` Série A rows) are de-duplicated by `{competition, season, home_key, away_key}` using a source-priority order.
