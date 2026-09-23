# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities, serverInfo | `mcp.rs:handle` |
| `ping` | `{}` | `mcp.rs:handle` |
| `tools/list` | array of 12 tool definitions | `mcp.rs:tool_definitions` |
| `tools/call` | `{content:[{type:text}]}` (or `isError`) | `mcp.rs:call_tool` |
| notifications (no `id`) | — (None) | `mcp.rs:handle` |
| unknown method | JSON-RPC error `-32601` | `mcp.rs:handle` |

## MCP tools (12)

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team/opponent/venue/competition/season/date range/round |
| `head_to_head` | Head-to-head W/L/D record + match list between two teams |
| `team_stats` | Team W/D/L + goals record, optional season/competition/venue, breakdown by competition |
| `standings` | Season league table computed from matches (champion + relegation zone) |
| `rank_teams` | Rank teams by metric: win_rate / goals / defense / home / away |
| `biggest_wins` | Largest victory margins, optionally filtered |
| `league_stats` | Aggregate: avg goals/match, home/away/draw rates, per-season trend, extended stats |
| `team_competitions` | Which competitions a team appears in, across all files |
| `derbies` | Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, …) |
| `search_players` | FIFA players by name/nationality/club/position group/min overall |
| `brazilian_club_players` | Players at Brazilian clubs joined with each club's match record |
| `dataset_info` | Summary of loaded datasets + de-dup counts |

## CLI

`brazilian-soccer-mcp [DATA_DIR]` — data dir from argv[1], else `$SOCCER_DATA_DIR`, else `data/kaggle`. Reads JSON-RPC requests line-by-line from stdin, writes responses to stdout.

## Data schema (in-memory)

- `Match`: date (ISO), season, competition (enum), round/stage, home/away (display + canonical key), home/away goals, arena, source file, optional extended stats `[6]` (corners/attacks/shots).
- `Player`: id, name, age, nationality, overall, potential, club (+ key), position, jersey, height, weight, value, skills `Vec<(name, rating)>`.
- `Dataset`: `matches`, `players`, `display` (key→preferred name), `file_counts`.
- Loads 6 CSVs from `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro, fifa_data.
