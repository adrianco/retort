# Interfaces

## MCP tools (`server.py`, FastMCP over stdio)

| Tool | Purpose | Backing query |
|------|---------|---------------|
| `search_matches` | Matches by team/opponent/competition/season/date range/stage/venue | `queries.search_matches` |
| `last_meeting` | Most recent match between two clubs | `queries.last_meeting` |
| `head_to_head` | H2H wins/draws/goals + match list | `queries.head_to_head` |
| `derbies` | Matches between traditional rivals | `queries.derbies` |
| `team_statistics` | W/D/L, goals, points for a club (season/comp/venue) | `queries.team_stats` |
| `team_profile` | Span, per-competition record, squad | `queries.team_profile` |
| `compare_teams` | Two clubs side-by-side + H2H | `queries.compare_teams` |
| `home_away_split` | Home vs away record | `queries.home_away_split` |
| `find_teams` | Disambiguate club names | `queries.list_teams` |
| `search_players` | FIFA players by name/nationality/club/position/rating | `queries.search_players` |
| `player_profile` | One player + club match context | `queries.player_profile` |
| `club_squad` | Highest-rated FIFA players at a club | `queries.club_squad` |
| `players_by_club` | Players of a nationality aggregated per club | `queries.players_by_club_summary` |
| `standings` | League table computed from matches | `queries.standings` |
| `competition_summary` | Coverage + aggregates for a competition | `queries.competition_summary` |
| `knockout_bracket` | Cup matches grouped by stage | `queries.knockout_bracket` |
| `list_competitions` | Competitions/seasons/source coverage | `queries.list_competitions` |
| `biggest_wins` | Largest margins of victory | `queries.biggest_wins` |
| `team_rankings` | Rank clubs by metric (points/wins/win_rate/…) | `queries.team_rankings` |
| `compare_seasons` | Aggregate stats across several seasons | `queries.compare_seasons` |
| `dataset_statistics` | Dataset-wide goals/match, home-win rate | `queries.overall_statistics` |

## MCP resources

| URI | Returns |
|-----|---------|
| `soccer://overview` | Competition/season coverage summary |
| `soccer://teams` | All clubs with match data + ids + match counts |

## CLI

| Command | Purpose |
|---------|---------|
| `python -m brazilian_soccer.server` | Serve MCP over stdio (`make serve`) |
| `python -m brazilian_soccer.demo` | Answer the spec's sample questions (`make demo`) |
| `brazilian-soccer-mcp` | Console-script entry point → `server:main` |

## Data schema (loaded, not persisted)

- **Match**: match_id, competition, season, date, home/away team ids, home/away goals, round, stage, venue, sources, stats (corners/shots/attacks).
- **Player**: player_id, name, age, nationality, overall, potential, club, club_team_id, position, physicals, skills{}.
- **Team**: team_id (canonical slug), name, state, country, aliases.
- Sources: `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv` (all six under `data/kaggle/`).
