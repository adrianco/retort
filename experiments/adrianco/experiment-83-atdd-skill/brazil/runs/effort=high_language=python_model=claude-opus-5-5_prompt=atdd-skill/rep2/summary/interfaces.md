# Interfaces

## HTTP routes

(none) — this is an MCP (Model Context Protocol) server over stdio, not an HTTP service.

## MCP tools

Exposed by `server.py:build_server()` via `@server.tool()`; each returns a `CallToolResult`
with both formatted text and structured JSON. A `QueryError` from the knowledge base is
re-raised as an MCP `ToolError`.

| Tool | Key parameters | Returns | Backing method |
|------|----------------|---------|----------------|
| find_matches | team, opponent, venue, competition, season, date_from, date_to, stage, limit | matches + optional head-to-head | `knowledge.find_matches` |
| head_to_head | team, opponent, competition | wins/draws/goals, recent + last meeting | `knowledge.head_to_head` |
| team_record | team, season, competition, venue | played/W/D/L, goals, win rate, by-competition | `knowledge.team_record` |
| team_competitions | team | competitions with match counts + seasons | `knowledge.team_competitions` |
| club_profile | team | match record + competitions + FIFA squad | `knowledge.club_profile` |
| league_table | season, competition | standings, champion, relegated | `knowledge.league_table` |
| top_scoring_teams | season, competition, limit | teams ranked by goals | `knowledge.top_scoring_teams` |
| knockout_bracket | competition, season | cup ties/legs/aggregates by stage | `knowledge.knockout_bracket` |
| competition_summary | competition, season | match/goal aggregates, result-split rates | `knowledge.competition_summary` |
| compare_seasons | season, other_season, competition | per-season stats + champion | `knowledge.compare_seasons` |
| biggest_wins | competition, season, team, limit | matches by goal margin | `knowledge.biggest_wins` |
| best_records | venue, competition, season, min_matches, limit | teams ranked by win rate | `knowledge.best_records` |
| find_derbies | season, competition, rivalry | rival matches with rivalry name | `knowledge.find_derbies` |
| search_players | name, nationality, club, position, min_overall, limit | players, highest rated first | `knowledge.search_players` |
| player_profile | name | full FIFA profile (+ similar-name fallback) | `knowledge.player_profile` |
| brazilian_players_by_club | nationality, brazilian_clubs_only | per-club counts + avg rating | `knowledge.brazilian_players_by_club` |
| dataset_overview | (none) | loaded datasets, row counts, season coverage | `knowledge.dataset_overview` |

Server metadata: name `brazilian-soccer`, version `1.0.0`, with `INSTRUCTIONS` describing
coverage and naming conventions. (17 tools; `find_matches` folds in head-to-head when both
team and opponent are given.)

## CLI

`python -m brazilian_soccer_mcp [--data-dir DIR]` — runs the server over stdio.
Data dir also settable via `BRAZILIAN_SOCCER_DATA_DIR`; default `data/kaggle`.

## Library API

`SoccerKnowledge(data_dir)` is the queryable core; its public methods map 1:1 to the MCP
tools above and each returns an `Answer(text, data)`. Query failures raise `QueryError`.

## Data inputs (not a declared schema — read from CSV)

Six Kaggle CSVs loaded by `datasets.load_all()`, each with its own columns/date format,
normalized into:
- `RawMatch`: source, competition, season, date, home, away, home_goals, away_goals, round, stage, arena, statistics
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, height, weight, value, wage, preferred_foot, skills

Canonical competitions: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.
Records recorded by multiple datasets are merged into one `Match`; contradictory league
records are discarded.
