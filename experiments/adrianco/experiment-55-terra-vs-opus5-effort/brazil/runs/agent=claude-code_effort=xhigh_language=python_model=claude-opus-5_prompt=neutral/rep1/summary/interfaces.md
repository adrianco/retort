# Interfaces

## MCP tools

24 tools, defined once in `tools.py` (`@tool`) and re-exposed as typed MCP wrappers in `server.py` (`@server.tool`). Each returns rendered text plus a JSON `data` payload. Unresolvable club/competition names return a helpful message with suggestions instead of raising.

| Tool | Key arguments | Answers |
|------|---------------|---------|
| search_matches | team, opponent, competition, season, date_from/to, home_away, stage, round, limit | "What matches did Palmeiras play in 2023?" |
| head_to_head | team_a, team_b, competition, season, limit | "Flamengo vs Fluminense record" |
| find_derbies | season, competition, derby, limit | "Show me all derbies in 2023" |
| team_stats | team, competition, season, scope | "Corinthians home record in 2022" |
| team_profile | team, season | Full club picture |
| compare_teams | team_a, team_b, competition, season | "Compare Palmeiras and Santos" |
| best_records | competition, season, scope, metric, min_matches, limit | "Best away record" |
| top_scoring_teams | competition, season, limit | "Most goals in Serie A 2023" |
| competition_standings | season, competition, scope, limit | "Who won the 2019 Brasileirão?" |
| competition_champion | competition, season | Table winner / cup-final winner |
| relegated_teams | season, competition, slots | "Relegated in 2020" |
| competition_stats | competition, season | Goals/match, home advantage, draw rate |
| biggest_wins | competition, season, team, limit | "Biggest wins in the dataset" |
| compare_seasons | seasons[], competition | "Compare 2018 and 2019" |
| search_players | name, nationality, club, position, min_overall, max_age, brazilian_clubs_only, sort_by, limit | "Brazilian players", "forwards from São Paulo" |
| player_profile | name | "Who is Neymar?" |
| club_squad | club, limit | "Which players play for Grêmio?" (cross-file) |
| brazilian_club_squads | limit | Squad size + avg rating per club |
| resolve_team | query, limit | Disambiguate "Botafogo"/"América"/"Atlético" |
| list_teams | state, country, competition, search, limit | Club listing |
| list_competitions | (none) | Competitions + season coverage |
| dataset_summary | (none) | Provenance, licences, graph shape |
| graph_neighbors | node_id, relation, direction, limit | Raw KG traversal |
| position_groups | (none) | FIFA codes per position group |

## MCP resources

| URI | MIME | Returns |
|-----|------|---------|
| soccer://datasets | application/json | Source CSVs, licences, row counts (from `dataset_summary`) |
| soccer://competitions | application/json | Competitions with season coverage + match counts |
| soccer://teams | application/json | Every club in the graph with match count |
| soccer://graph/schema | application/json | Node/edge type counts |

## MCP prompts

| Prompt | Args | Purpose |
|--------|------|---------|
| analyze_team | team | Guided multi-tool club analysis |
| season_review | competition, season | Guided season report |

## CLI (`brazilian-soccer-mcp`)

| Subcommand | Flags/args | Description |
|------------|-----------|-------------|
| serve | --transport {stdio,sse,streamable-http} | Run the MCP server |
| tools | — | List tools + argument help |
| summary | — | Print dataset coverage report |
| call | TOOL key=value..., --args JSON, --json | Invoke one tool directly |

## Knowledge-graph schema

Node types: `competition`, `season`, `team`, `match`, `player`, `venue`. Ids are namespaced strings (`team:flamengo-rj`, `competition:serie-a`, `player:190871`, `match:brasileirao:12`).

Edge types (directed, traversable in/out/both):

`match --home_team--> team`, `match --away_team--> team`, `match --in_competition--> competition`, `match --in_season--> season`, `match --played_at--> venue`, `season --of_competition--> competition`, `team --competed_in--> competition`, `player --plays_for--> team`.

## Data schemas (dataclasses, `models.py`)

- `Team`: id, name, state, country, nicknames, aliases; `display_name`.
- `Match`: id, competition_id, season, date, home/away team ids + raw names, home/away goals, kickoff, round, stage, venue, sources[], stats{}; derived `has_score`, `total_goals`, `goal_difference`, `result`, `winner_id`, `goals_for/against()`.
- `Player`: id, name, age, nationality, overall, potential, club_raw, club_team_id, position, jersey, physicals, skills{}; `is_brazilian`, `top_skills()`.
- `TeamRecord`: played/wins/draws/losses/goals; derived `points`, `goal_difference`, `win_rate`, `points_per_game`.
- `StandingRow`: position + record + note ("Champion"/"Relegated"). `HeadToHead`: two-club aggregate. `Competition`: id/name/short_name/kind/aliases.
