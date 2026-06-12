# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio (newline-delimited messages). Protocol version
`2024-11-05`. Diagnostics go to stderr to keep stdout clean.

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities, serverInfo | `bsmcp_mcp:dispatch/3` |
| `tools/list` | tool catalog (6 tools) | `bsmcp_mcp:dispatch/3` → `bsmcp_tools:list/0` |
| `tools/call` | `{content:[text], isError}` | `bsmcp_mcp:dispatch/3` → `bsmcp_tools:call/3` |
| `ping` | `{}` | `bsmcp_mcp:dispatch/3` |
| (notification, no id) | no reply | `bsmcp_mcp:handle_request/2` |
| (unknown method) | error -32601 | `bsmcp_mcp:dispatch/3` |
| (bad JSON) | error -32700 parse error | `bsmcp_server:process_line/2` |

## MCP tools

| Tool | Required args | Optional args | Backed by |
|------|---------------|---------------|-----------|
| `find_matches` | – | team, opponent, home_team, away_team, season, competition, limit | `bsmcp_query:find_matches/2` |
| `head_to_head` | team_a, team_b | – | `bsmcp_query:head_to_head/3` |
| `team_record` | team | season, competition, home_only, away_only | `bsmcp_query:team_record/3` |
| `find_players` | – | name, nationality, club, position, min_overall, limit | `bsmcp_query:find_players/2` |
| `standings` | competition, season | – | `bsmcp_query:standings/3` |
| `match_statistics` | – | competition, season, team | `avg_goals/1`, `home_win_rate/1`, `biggest_wins/2` |

## Data schema (in-memory)

Store: `#{matches => [match()], players => [player()]}`.

Canonical match map: `competition, home, away, home_norm, away_norm,
home_goal, away_goal, season, round, date, stage` (BR-Football rows add
`home_shots, away_shots, home_corner, away_corner`).

Player map: `id, name, age, nationality, overall, potential, club,
club_norm, position, jersey, name_norm, nationality_norm`.

## Data sources

Loads 5 match CSVs (Brasileirão, Copa do Brasil, Libertadores,
BR-Football extended stats, novo_campeonato historical) + `fifa_data.csv`
from `data/kaggle/`. Cross-file fixtures deduplicated by (date, home_norm,
away_norm).

## CLI

`bsmcp [data-dir]` — escript entry point; default data-dir `data/kaggle`.
