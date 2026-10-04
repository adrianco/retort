# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio, newline-delimited)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo, instructions | `server.ex:dispatch/3` |
| ping | `{}` | `server.ex:dispatch/3` |
| tools/list | `{tools: [...]}` (14 tool defs) | `server.ex` → `Tools.list/0` |
| tools/call | `{content: [{type:text}], isError}` | `server.ex` → `Tools.call/2` |

Supported protocol versions: `2024-11-05` (default), `2025-03-26`, `2025-06-18`.
JSON-RPC batches and notifications (no `id`) are handled. Errors use standard codes
(-32700 parse, -32600 invalid request, -32601 method not found, -32602 invalid params,
-32603 internal). serverInfo name `brazilian-soccer-mcp`, version `0.1.0`.

## MCP tools (14)

| Tool | Required args | Optional args | Purpose |
|------|---------------|---------------|---------|
| search_matches | (none) | team, opponent, venue, competition, season, date_from, date_to, round, stage, limit | Find matches; adds head-to-head when team+opponent given |
| head_to_head | team_a, team_b | competition, season, limit | Two-team comparison: wins/draws/goals + meetings |
| team_stats | team | season, competition, venue | W/D/L record, goals, win rate (overall/home/away/per-competition) |
| team_profile | team | — | Cross-dataset profile: competitions, record, recent matches, FIFA squad |
| standings | season | competition | League table (3 pts/win), marks champion & relegated |
| team_rankings | (none) | sort_by, venue, competition, season, min_matches, limit | Rank teams by win_rate/points/wins/goals/GD etc. |
| competition_stats | (none) | competition, season, team | Aggregate: matches, goals/match, home/away/draw rates, avg corners |
| compare_seasons | season_a, season_b | competition | Side-by-side season comparison |
| biggest_wins | (none) | team, competition, season, by (margin\|total_goals), limit | Largest margins / highest-scoring matches |
| derbies | (none) | season, competition, team, limit | Matches between traditional rivals |
| search_players | (none) | name, nationality, club, position, min_overall, max_age, sort_by, limit | Search FIFA players |
| player_details | name | — | Full player profile: ratings, physicals, top skills |
| players_by_club | (none) | nationality, position, brazilian_clubs_only, limit | Players grouped by club with counts/avg rating |
| dataset_info | (none) | — | Files, row counts, competitions, season coverage |

All tools return plain-text human-readable output (not structured JSON) in the MCP
text content block. Required-arg checking is done in `Tools.check_required/2`.

## CLI

`mix soccer.mcp [DATA_DIR]` or the escript `brazilian_soccer_mcp [DATA_DIR]` — runs the
server on stdio. DATA_DIR defaults to `$BRAZILIAN_SOCCER_DATA_DIR` or `data/kaggle`.

## Library API

- `Queries`: matches/1, team_stats/2, head_to_head/3, team_competitions/1, table/2,
  standings/2, rankings/2, summary/1, biggest_wins/2, highest_scoring/2, derbies/1,
  compare_seasons/3, team_ref/1, record/2, competition/1, side/2
- `Players`: search/1, by_club/1
- `Teams`: resolve/2, same?/3, derby_name/2, brazilian_club?/1
- `Store`: data/0, matches/0, players/0, load/1
- `CSV`: parse/1, parse_maps/1
- `Text`: fold/1, parse_date/1, parse_int/1, blank?/1

## Data schema

`%Match{}`: date, time, season, competition, round, stage, home, away, home_key,
away_key, home_state, away_state, home_goals, away_goals, arena, stats, sources.

Player (map): id, name, age, nationality, overall, potential, club, position,
jersey_number, height, weight, preferred_foot, value, wage, skills (35 FIFA skill
ratings), plus folded/keyed lookup fields (name_fold, nationality_fold, club_fold,
club_key).

Datasets merged from 6 CSVs into 5 competitions: Brasileirão Série A / B / C,
Copa do Brasil, Copa Libertadores. Duplicate fixtures across files (same competition +
teams, dates within 2 days) are merged.
