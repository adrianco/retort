# Interfaces

## MCP tools (transport: stdio, SDK: rmcp 2.0)

| Tool | Purpose | Handler |
|------|---------|---------|
| `find_matches` | Filter matches by team/opponent/venue/competition/season/date range | `server.rs:find_matches` → `store.rs:find_matches` |
| `head_to_head` | Win/draw/loss + goal tallies between two teams | `server.rs:head_to_head` → `store.rs:head_to_head` |
| `team_record` | Single team's W/D/L, goals for/against, win rate | `server.rs:team_record` → `store.rs:team_record` |
| `standings` | League table computed from match results (CBF tiebreaks) | `server.rs:standings` → `store.rs:standings` |
| `biggest_wins` | Matches sorted by goal margin | `server.rs:biggest_wins` → `store.rs:biggest_wins` |
| `match_stats` | Aggregate avg goals + home/draw/away rates | `server.rs:match_stats` → `store.rs:match_stats` |
| `list_teams` | Distinct canonical team names (discovery helper) | `server.rs:list_teams` → `store.rs:list_teams` |
| `list_competitions` | Dataset overview: match counts + season ranges | `server.rs:list_competitions` → `store.rs:competitions_overview` |
| `search_players` | FIFA player search by name/nationality/club/position/min_overall | `server.rs:search_players` → `store.rs:search_players` |

## Data schema (in-memory)

`MatchRecord`: competition, datetime/date, home_team, away_team, home_goal, away_goal, season, round/stage (`model.rs:64`). Derived: `outcome()`, `goal_difference()`, `total_goals()`.

`PlayerRecord`: id, name, age, nationality, overall, potential, club, position, plus normalized search keys (`model.rs:115`).

`Competition` enum: Brasileirao, CopaDoBrasil, Libertadores, ExtendedStats, HistoricalBrasileirao (`model.rs:10`).

## Data sources

Six CSVs under `data/kaggle/` loaded at startup: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`.

## CLI / config

The binary resolves its data dir from (1) first CLI arg / `--data-dir`, (2) `BRAZIL_SOCCER_DATA_DIR` env var, (3) `data/kaggle` next to the cargo manifest (`main.rs:resolve_data_dir`).
