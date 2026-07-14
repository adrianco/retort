# Interfaces

## MCP tools (stdio transport, rmcp SDK)

Registered via `#[tool_router]` in `src/server.rs`; server name `brazilian-soccer-mcp` v0.1.0.

| Tool | Args | Backing query |
|------|------|---------------|
| `search_matches` | team, opponent, competition, season, date_from, date_to, limit | `queries::search_matches` |
| `compare_teams` | team_a, team_b, competition, season | `queries::compare_teams` |
| `team_record` | team, competition, season, venue (home/away/all) | `queries::team_record` |
| `standings` | competition, season | `queries::standings` |
| `team_leaderboard` | competition, season, metric, venue, limit | `queries::team_leaderboard` |
| `biggest_wins` | competition, season, limit | `queries::biggest_wins` |
| `average_stats` | competition, season | `queries::average_stats` |
| `derby_matches` | season, rivalry | `queries::derby_matches` |
| `team_competitions` | team | `queries::team_competitions` |
| `search_players` | name, nationality, club, position, min_overall, limit | `queries::search_players` |
| `brazilian_club_squads` | limit_clubs | `queries::brazilian_club_squads` |
| `list_datasets` | (none) | `queries::list_datasets` |

All tools return a human-readable formatted `String` (not structured JSON payloads); metric strings mirror the answer format shown in TASK.md.

## Data schema (in-memory)

`MatchRecord`: source_file, competition, date, date_display, season, round, stage, venue, home_team, away_team, home_team_key, away_team_key, home_state, away_state, home_identity, away_identity, home_goal, away_goal.

`Player`: id, name, age, nationality, overall, potential, club, club_key, position.

## Data sources (loaded at startup from `data/kaggle/`)

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`. Directory resolved from CLI arg → `SOCCER_DATA_DIR` → `./data/kaggle` → compile-time `CARGO_MANIFEST_DIR`.

## CLI

`brazilian-soccer-mcp [data_dir]` — single optional positional argument (data directory). No subcommands; the process is an MCP stdio server.
