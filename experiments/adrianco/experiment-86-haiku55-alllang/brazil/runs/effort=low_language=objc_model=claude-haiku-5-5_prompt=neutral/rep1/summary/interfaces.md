# Interfaces

## Transport

JSON-RPC 2.0 over newline-delimited stdio. Methods: `initialize`, `notifications/*`
(no response), `ping`, `tools/list`, `tools/call`. Protocol version `2024-11-05`.

## MCP Tools (`tools/call`)

| Tool | Purpose | Required args |
|------|---------|---------------|
| `search_matches` | Matches by team/opponent/competition/season/date range; H2H when team+opponent | — |
| `team_record` | W/D/L, goals, win rate for a team (by venue/competition/season) | `team` |
| `head_to_head` | Head-to-head record between two teams | `team`, `opponent` |
| `standings` | League table for a season, computed from results (3 pts win, 1 draw) | `season` |
| `league_stats` | Avg goals/match, home/draw/away % for a competition or season | — |
| `biggest_wins` | Largest winning margins, optionally filtered | — |
| `search_players` | FIFA players by name/nationality/club/position group/min overall | — |
| `brazilian_club_summary` | Brazilian players at Brazilian clubs: counts + avg overall | — |

## Data schemas

- `SoccerMatch`: date (ISO), season, competition (canonical), stage, home/away name+key, home/away goals, source.
- `SoccerPlayer`: id, name, age, nationality, overall, potential, club, position, value, wage.

## Data inputs

`data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
`Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`,
`fifa_data.csv` (18,207 players). Overlapping match sources are de-duplicated.
