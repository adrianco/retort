# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Required args | Optional args | Handler |
|------|---------------|---------------|---------|
| search_matches | (none) | team, opponent, competition, season, season_from, season_to, date_from, date_to, venue, limit | `bsoccer_query:search_matches/1` |
| head_to_head | team1, team2 | competition | `bsoccer_query:head_to_head/1` |
| team_record | team | season, competition, venue | `bsoccer_query:team_record/1` |
| standings | season | competition, limit | `bsoccer_query:standings/1` |
| search_players | (none) | name, nationality, club, position, min_overall, sort, limit | `bsoccer_query:search_players/1` |
| match_statistics | (none) | team, competition, season, season_from, season_to | `bsoccer_query:match_stats/1` |
| data_summary | (none) | (none) | `bsoccer_query:data_summary/1` |

## JSON-RPC methods

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities, serverInfo, instructions | `bsoccer_mcp.erl:dispatch/2` |
| notifications/initialized | noreply | `bsoccer_mcp.erl:dispatch/2` |
| ping | `{}` | `bsoccer_mcp.erl:dispatch/2` |
| tools/list | tool catalogue (7 tools w/ JSON-Schema inputSchema) | `bsoccer_mcp.erl:tools/0` |
| tools/call | `{content:[{type:text,text}], structuredContent}` or `isError:true` | `bsoccer_mcp.erl:call_tool/2` |

## CLI

| Invocation | Behaviour |
|------------|-----------|
| `bsoccer` | Serve MCP over stdio (data dir `data/kaggle`) |
| `bsoccer <data_dir>` | Serve using a custom data directory |
| `bsoccer --selftest [dir]` | Load data, print summary, run 3 demo queries, exit |

Env: `BSOCCER_DATA_DIR` overrides the default data directory.

## Data schema (ETS, in-memory)

`bsoccer_matches`: `{Id, #{competition, season, round, stage, date, date_tuple, home, away, home_key, away_key, home_ident, away_ident, home_full, away_full, home_goal, away_goal, source, extra}}` — loaded from 5 match CSVs.

`bsoccer_players`: `{Id, #{id, name, name_key, age, nationality, nationality_key, overall, potential, club, club_key, position, jersey, height, weight, foot, skills}}` — loaded from `fifa_data.csv`.
