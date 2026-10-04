# Interfaces

## HTTP routes

(none) — this is a stdio MCP server, not an HTTP service.

## MCP tools (JSON-RPC `tools/call`)

Fifteen tools, each declared in `SoccerTools.tools` (Tools.swift) with a JSON input schema and a text result.

| Tool | Purpose | Required args | Optional args |
|------|---------|---------------|---------------|
| `search_matches` | Matches by team/opponent/venue/competition/season/date/stage/round, with W-D-L or head-to-head summary | (none) | team, opponent, venue, competition, season, date_from, date_to, stage, round, include_stats, limit |
| `head_to_head` | Two teams compared: wins, draws, goals, home records, recent/biggest meeting | team_a, team_b | competition, season, date_from, date_to, limit |
| `team_stats` | One team's record with home/away, per-competition, per-season breakdowns | team | venue, competition, season, date_from, date_to |
| `team_profile` | Cross-dataset team overview: competitions/seasons, records, recent match, FIFA squad | team | limit |
| `league_standings` | League table from results (champion + relegation for Serie A) | season | competition |
| `knockout_bracket` | Cup season grouped by stage (Libertadores/Copa do Brasil) with final winner | season | competition, include_group_stage |
| `competition_stats` | Aggregate: matches, goals, avg goals/match, home/draw/away rates | (none) | team, competition, season, date_from, date_to |
| `compare_seasons` | Two seasons compared: goals, rates, leader, best attack/defence, biggest win | season_a, season_b | competition |
| `biggest_wins` | Largest winning margins, optionally filtered | (none) | team, competition, season, date_from, date_to, limit |
| `team_rankings` | Rank teams by metric (points/wins/win_rate/goals_for/goals_against/goal_difference/points_per_game) | (none) | metric, venue, competition, season, date_from, date_to, min_matches, limit |
| `find_derbies` | Matches between traditional rivals | (none) | team, competition, season, date_from, date_to, limit |
| `search_players` | FIFA players by name/nationality/club/position/rating/age | (none) | name, nationality, club, position, min_overall, max_age, limit |
| `player_details` | Full profile of one player incl. attributes | name | all_attributes |
| `club_player_summary` | Player counts + average rating per club (defaults to Brazilian) | (none) | nationality, position, min_overall, brazilian_clubs_only, limit |
| `dataset_summary` | Coverage: files, competitions, season ranges, team/player counts | (none) | (none) |

## JSON-RPC methods (MCPServer.handle)

| Method | Behaviour |
|--------|-----------|
| `initialize` | Echoes protocolVersion (default `2024-11-05`), advertises `tools` capability, returns serverInfo + instructions |
| `ping` | Empty result |
| `tools/list` | Returns all 15 tool schemas |
| `tools/call` | Runs the named tool; errors are returned as `content` text with `isError: true` |
| `resources/list`, `prompts/list` | Empty arrays |
| unknown | JSON-RPC error `-32601` (method not found); parse/invalid-request errors `-32700`/`-32600` |

## CLI

`brazilian-soccer-mcp [--data-dir <path to data/kaggle>]` — reads JSON-RPC lines from stdin, writes responses to stdout, diagnostics to stderr. Data dir is also resolvable via `BRAZILIAN_SOCCER_DATA_DIR` or by walking up from the cwd / binary path.

## Library API

Public types are exported from module `BrazilianSoccer`: `DataStore`, `SoccerTools`, `MCPServer`, `Tool`, `MatchFilter`, `DataStore.PlayerFilter`, and the model/value types (`Match`, `Player`, `Record`, `SimpleDate`, `Competition`, `Venue`, `TeamNames`, `TeamResolver`, `CSV`).

## Data schema

In-memory only (no database). Six Kaggle CSVs are parsed into two collections:

- `Match`: competition (enum), date (`SimpleDate`), season (Int), home/away (canonical keys), homeGoals/awayGoals (Int), optional round/stage/arena, optional `MatchStats` (corners/attacks/shots), source-file list. Same fixture appearing across files within 2 days is merged.
- `Player`: id, name, age?, nationality, overall, potential, club, clubKey, position, jerseyNumber?, height, weight, value, wage, preferredFoot, `[(name, value)]` skill attributes.
