# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion, capabilities.tools, serverInfo, instructions | `server.ex:dispatch/4` |
| `ping` | `{}` | `server.ex:dispatch/4` |
| `tools/list` | `{tools: [...6 definitions...]}` | `server.ex` → `tools.ex:definitions/0` |
| `tools/call` | `{content: [{type: text}], isError}` | `server.ex` → `tools.ex:call/3` |

Notifications (no `id`) get no response; unknown methods return `-32601`, bad params `-32602`, parse errors `-32700`.

## MCP tools (the query surface)

| Tool | Answers | Key args |
|------|---------|----------|
| `search_matches` | Matches by team/opponent/competition/season/venue/stage/date range; adds head-to-head summary when team+opponent given | team, opponent, competition, season, venue, stage, date_from, date_to, limit |
| `team_stats` | W/D/L record, goals for/against, win rate for a team | team (req), competition, season, venue |
| `head_to_head` | Record between two teams across all competitions + recent matches | team_a (req), team_b (req), limit |
| `competition_standings` | League table computed from results (3/1/0 points) | competition (req), season (req) |
| `search_players` | FIFA players by name/nationality/club/position/min_overall, sorted by overall | name, nationality, club, position, min_overall, limit |
| `match_statistics` | `averages`, `biggest_wins`, `best_home`, `best_away` | kind (req), competition, season, limit |

## CLI

`soccer_mcp [--data-dir PATH]` — data dir defaults to `$SOCCER_DATA_DIR` then `data/kaggle`. Diagnostics to stderr; protocol to stdout.

## Data schema (internal)

- `Match`: date, competition, season, stage, home/away (display), home_key/away_key (normalized), home_state/away_state, home_goals/away_goals, source.
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, …
- `Store`: `matches: [Match]`, `players: [Player]`, `sources: [{file, count}]`.

## Data sources loaded (R2)

All six CSVs in `data/kaggle/` are read: Brasileirao_Matches, novo_campeonato_brasileiro, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset (matches), fifa_data (players). After de-dup: ~17,545 matches, >18,000 players.
