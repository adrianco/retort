# Interfaces

## MCP transport

stdio, newline-delimited JSON-RPC 2.0, protocol `2024-11-05`. Methods: `initialize`,
`ping`, `tools/list`, `tools/call`, `notifications/*` (no reply). See `mcp_server.ex`.

## MCP tools (`tools.ex:definitions/0`)

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Filter matches | team, opponent, venue, season, competition, date_from, date_to, stage, limit |
| `head_to_head` | H2H record + recent matches | team_a*, team_b*, competition, season, limit |
| `team_stats` | W/D/L, goals for/against, win rate | team*, season, competition, venue |
| `team_competitions` | Competitions/seasons a team appears in | team* |
| `standings` | League table computed from results | season*, competition, limit |
| `cup_finals` | Copa do Brasil / Libertadores finals | competition, season |
| `competition_stats` | Avg goals, home/away/draw rates | competition, season, team |
| `biggest_wins` | Largest victory margins | competition, season, team, limit |
| `best_records` | Rank teams by win rate | venue, competition, season, min_matches, limit |
| `top_scoring_teams` | Teams by goals in a league season | season*, competition, limit |
| `derbies` | Matches between traditional rivals | season, competition, limit |
| `compare_seasons` | Compare two league seasons | season_a*, season_b*, competition |
| `search_players` | FIFA players by name/nat/club/pos/rating | name, nationality, club, position, min_overall, limit |
| `club_profile` | Cross-dataset: match record + FIFA squad | team*, season, limit |
| `players_by_club` | Player counts + avg rating per club | nationality, limit |

(* = required arg)

## Data schema (normalized in `data.ex`)

- **Match**: date, season, home, away, home_key, away_key, home_goal, away_goal,
  competition (`:serie_a | :serie_b | :serie_c | :copa_do_brasil | :libertadores`),
  round, stage, source, plus per-source extras (arena, stats).
- **Player**: id, name, name_key, age, nationality, overall, potential, club,
  club_key, position, jersey, height, weight, value, wage, foot, skills{}.

Data source: 5 match CSVs + `fifa_data.csv` under `data/kaggle/` (18,207 players),
loaded once into `:persistent_term` with cross-file dedup.
