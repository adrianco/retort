# Interfaces

## Transport

JSON-RPC 2.0 over stdio, one message per line (`main.c` reads stdin line by line, `mcp.c:mcp_handle`). MCP methods: `initialize`, `ping`, `tools/list`, `tools/call`, plus notifications (no `id` → no reply).

## MCP tools (12)

| Tool | Purpose | Required args |
|------|---------|---------------|
| search_matches | Filter matches by team/opponent/competition/season/date range/venue/stage | (none) |
| head_to_head | H2H record + recent matches between two teams | team1, team2 |
| team_stats | W/D/L, goals for/against, by season/competition/venue | team |
| standings | League table for a season computed from results (champion + relegation) | season |
| search_players | FIFA player search by name/nationality/club/position/min rating | (none) |
| players_by_brazilian_club | Count + avg rating of players (default Brazil) at Brazilian clubs | (none) |
| biggest_wins | Largest victory margins | (none) |
| competition_stats | Avg goals/match, home/away win + draw rates | (none) |
| best_records | Rank teams by win rate (overall/home/away) | (none) |
| team_competitions | Which competitions a team appears in + seasons covered | team |
| derbies | Traditional rivalry matches (Fla-Flu, Grenal, ...) | (none) |
| compare_seasons | Compare aggregate stats + champions of two seasons | season1, season2 |

## Data schema (in-memory)

- `match_t`: date, home, away, hkey, akey, hg, ag, season, comp, stage, source, corners_h/a, shots_h/a.
- `player_t`: id, name, nationality, club, position, overall, potential, age, jersey, height, weight, value, foot, nkey, ckey.
- Loaded from `data/kaggle/`: Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, novo_campeonato_brasileiro.csv, BR-Football-Dataset.csv (matches), fifa_data.csv (players). Matches de-duplicated across overlapping files by (comp|season|home|away), Libertadores keyed by date.
