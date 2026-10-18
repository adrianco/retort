# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Behaviour | Handler |
|--------|-----------|---------|
| `initialize` | Echoes protocolVersion, advertises `tools` capability, serverInfo | `mcp.c:handle_message` |
| `ping` | Empty result `{}` | `mcp.c:handle_message` |
| `tools/list` | Returns the 7 tool definitions with inputSchema | `mcp.c` → `query.c:query_tools_json` |
| `tools/call` | Dispatches to a tool, wraps text in `content[]` with `isError` | `mcp.c:handle_call` → `query.c:query_run` |
| notifications (no id) | Silently ignored (never answered) | `mcp.c:handle_message` |

JSON-RPC errors: `-32700` parse, `-32600` invalid request, `-32601` method not found, `-32602` invalid params / unknown tool.

## Tools

| Tool | Purpose | Key args |
|------|---------|----------|
| `find_matches` | Matches by team/opponent/competition/stage/season/date range, recent first | team, opponent, competition, stage, season, date_from, date_to, venue, limit |
| `team_record` | W/D/L, goals for/against, win rate for a team | team (req), season, competition, venue, date_from, date_to |
| `head_to_head` | H2H record between two teams + recent meetings | team_a (req), team_b (req), competition, season |
| `standings` | League table computed from match results (3/1/0) | season (req), competition |
| `match_stats` | Match count, avg goals, home/draw/away rates, biggest wins | competition, season, stage, date_from, date_to |
| `search_players` | FIFA players by name/nationality/club/position/min_overall | name, nationality, club, position, min_overall, limit |
| `club_summary` | Clubs ranked by player count with avg overall | nationality, limit |

## Data schema (in-memory, loaded from CSV)

- **Match**: ymd, iso, season, is_final, home_goals, away_goals, competition, stage, home/away key + display name.
- **Team**: key (base+qualifier), base, qual (state/country), display name, match count.
- **Player**: id, age, overall, potential, jersey, name, nationality, club, position, value.

## Data sources (`data/kaggle/`)

Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv (competition mapped per-row), fifa_data.csv (players). Overlapping (competition, season) pairs are de-duplicated with the first listed source winning.

## CLI

`brazilian-soccer-mcp [data-dir]` — data dir also settable via `SOCCER_DATA_DIR`, default `data/kaggle`.
