# Interfaces

## MCP tools (FastMCP, registered in `server.py`)

| Tool | Key params | Returns | Delegates to |
|------|-----------|---------|--------------|
| search_matches | team, opponent, home, away, season, competition, start_date, end_date, limit | formatted match list | `tools.search_matches` → `kb.find_matches` |
| head_to_head | team_a, team_b, season, competition | head-to-head W/D + goals | `tools.head_to_head` → `kb.head_to_head` |
| team_record | team, season, competition, venue | W/L/D + goals + points | `tools.team_record` → `kb.team_record` |
| standings | season, competition, limit | computed league table | `tools.standings` → `kb.standings` |
| search_players | name, nationality, club, position, min_overall, limit | ranked player list | `tools.search_players` → `kb.search_players` |
| players_by_club | nationality, limit | per-club counts + avg rating | `tools.players_by_club` |
| statistics | competition, season | avg goals/match + home win rate | `tools.statistics` |
| biggest_wins | competition, season, limit | largest-margin victories | `tools.biggest_wins` |
| best_record | venue, competition, season, min_matches, limit | teams ranked by win-rate | `tools.best_record` |
| data_summary | — | match/player counts by competition | `tools.data_summary` |

## Library API

`KnowledgeBase.load(data_dir)` builds the in-memory store; `SoccerTools(kb)` wraps it for formatting; `build_server(kb=None)` returns a `FastMCP` instance (loads real data when `kb` is None).

## Data schema (in-memory dataclasses)

- `Match`: competition, season, date, round, stage, home_team, away_team, home_goal, away_goal, source; derived `home_key`/`away_key` (normalized), `winner`, `total_goals`.
- `Player`: player_id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight; derived `club_key`.

## Data sources

`data/kaggle/`: novo_campeonato_brasileiro.csv, Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, fifa_data.csv. 20,914 matches + 18,207 players loaded.

## HTTP routes / CLI commands

(none) — transport is MCP stdio (`python -m brazilian_soccer.server`).
