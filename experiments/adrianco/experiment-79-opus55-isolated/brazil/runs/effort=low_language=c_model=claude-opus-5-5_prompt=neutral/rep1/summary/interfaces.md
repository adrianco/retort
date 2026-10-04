# Interfaces

## MCP protocol (JSON-RPC over stdio)

| Method | Handler | Notes |
|--------|---------|-------|
| initialize | `mcp.c:mcp_handle` | Negotiates protocol version (2025-06-18 default), advertises `tools` capability |
| ping | `mcp.c:mcp_handle` | Returns `{}` |
| tools/list | `mcp.c:write_tools` | Emits generated JSON Schema per tool |
| tools/call | `mcp.c:run_tool` | Maps arguments onto `Params`, dispatches to `q_*` |

## MCP tools (15)

| Tool | Required args | Handler |
|------|---------------|---------|
| search_matches | — | `soccer.c:q_search_matches` |
| head_to_head | team, opponent | `soccer.c:q_head_to_head` |
| team_stats | team | `soccer.c:q_team_stats` |
| team_competitions | team | `soccer.c:q_team_competitions` |
| team_profile | team | `soccer.c:q_team_profile` |
| standings | season | `soccer.c:q_standings` |
| team_rankings | — | `soccer.c:q_team_rankings` |
| competition_stats | — | `soccer.c:q_competition_stats` |
| compare_seasons | season, season_b | `soccer.c:q_compare_seasons` |
| biggest_wins | — | `soccer.c:q_biggest_wins` |
| derbies | — | `soccer.c:q_derbies` |
| search_players | — | `soccer.c:q_search_players` |
| player_details | name | `soccer.c:q_player_details` |
| players_by_club | — | `soccer.c:q_players_by_club` |
| dataset_info | — | `soccer.c:q_dataset_info` |

## CLI

`brsoccer-mcp [--data DIR] [--call TOOL [JSON_ARGS]]` — default mode is the stdio MCP loop; `--call` invokes one tool and prints its text. Data dir resolves from `--data`, then `$BRSOCCER_DATA_DIR`, then `./data/kaggle`.

## Data schema

Six CSVs loaded into memory (`data/kaggle/`): `Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv` (matches) and `fifa_data.csv` (players). Matches are de-duplicated across sources into a single `Match[]` sorted by date; teams are normalized into a `Team[]` with base name + state + display name.
