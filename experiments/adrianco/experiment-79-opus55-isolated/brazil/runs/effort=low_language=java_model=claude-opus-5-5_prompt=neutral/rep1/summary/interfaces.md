# Interfaces

## Transport

MCP server speaking JSON-RPC 2.0 over stdio (one message per line), not HTTP.
Handled methods: `initialize`, `ping`, `tools/list`, `tools/call`. Unknown methods
return JSON-RPC error `-32601`; parse/validation failures return `-32700` / `-32600` /
`-32602`; notifications (no `id`) produce no response.

## MCP tools (`tools/call`)

| Tool | Required args | Optional args | Returns (text) |
|------|---------------|---------------|----------------|
| search_matches | — | team, opponent, venue, competition, season, date_from, date_to, stage, limit | Matching matches, most recent first; head-to-head tally when team+opponent given |
| head_to_head | team_a, team_b | competition, season | Wins/draws/goals, home/away split, recent meetings |
| team_stats | team | season, competition, venue | Record: matches, W/D/L, goals, win rate, splits, per-competition breakdown |
| standings | season | competition | League table from results; champion + relegated for complete Serie A seasons |
| team_rankings | — | metric, venue, competition, season, min_matches, limit | Teams ranked by chosen metric |
| match_statistics | — | competition, season | Avg goals/match, home-win/draw/away-win rates, corners, shots |
| biggest_wins | — | competition, season, team, limit | Matches by largest winning margin |
| compare_seasons | season_a, season_b | competition | Aggregate stats of two seasons compared |
| derbies | — | season, competition, team, limit | Matches between traditional rivals |
| knockout_stages | season | competition | Cup bracket by stage with aggregate scores |
| search_players | — | name, nationality, club, position, min_overall, limit | FIFA players, highest rated first |
| player_details | name | — | Full player profile (ratings, physical, skill attributes) |
| players_by_club | — | nationality, brazilian_clubs_only, limit | Player count + average rating grouped by club |
| club_profile | team | — | Cross-dataset club view: match record by competition + FIFA squad |
| dataset_info | — | — | Files loaded, row counts, competitions and seasons covered |

Argument coercion is lenient: numbers accept string forms, dates accept `YYYY-MM-DD` or
`DD/MM/YYYY`, and bad input is returned in-band with `isError: true` so the model can retry.

## Data schemas

**Match** (merged fixture): date, competition, season, round, stage, homeKey, awayKey,
homeGoals, awayGoals, stadium, homeCorners/awayCorners/homeShots/awayShots, sources.

**Player** (FIFA row): id, name, age, nationality, overall, potential, club, position,
jersey, height, weight, value, wage, foot, skills (map of ~17 skill columns).

## Input datasets (`data/kaggle/`, loaded at startup)

`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv` (Serie A historical),
`Brazilian_Cup_Matches.csv` (Copa do Brasil), `Libertadores_Matches.csv`,
`BR-Football-Dataset.csv` (extended, multi-tournament), `fifa_data.csv` (players).
Data dir resolves from `$BR_SOCCER_DATA_DIR`, else `./data/kaggle`.

## CLI

`McpServer.main([dataDir])` — optional first arg overrides the data directory; otherwise
runs the stdio server loop.
