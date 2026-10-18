# Interfaces

## MCP / JSON-RPC methods (stdio, newline-delimited)

| Method | Returns | Notes |
|--------|---------|-------|
| `initialize` | protocolVersion `2024-11-05`, capabilities, serverInfo | server `brazilian-soccer-mcp` v0.1.0 |
| `ping` | `{}` | |
| `tools/list` | array of tool name/description/inputSchema | lists the 9 tools below |
| `tools/call` | `{content:[{type:"text",text}], isError}` | tool exceptions returned as `isError:true` text |
| `notifications/*` | (no response) | notifications and id-less messages produce no reply |

Standard JSON-RPC error codes are used: parse (-32700), invalid request (-32600), method not found (-32601), invalid params (-32602), internal (-32603).

## MCP tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches, newest first | team, opponent, venue, competition, season, from, to, round, limit (default 20) |
| `head_to_head` | H2H record + matches between two teams | team (req), opponent (req), competition, season, limit (15) |
| `team_record` | Wins/draws/losses/goals for a team | team (req), competition, season, venue |
| `standings` | League table from match results (3pts/win) | competition (default Brasileirão), season (req), limit (20) |
| `league_stats` | Goals/match, home/draw/away rates | competition, season |
| `biggest_wins` | Largest winning margins | competition, season, limit (10) |
| `search_teams` | Resolve partial name to dataset spelling | query, limit (20) |
| `search_players` | FIFA player search, sorted by overall | name, nationality, club, position, min_overall, limit (20) |
| `club_summary` | Squad size + avg rating per club | nationality, limit (20) |

## CLI

| Invocation | Effect |
|------------|--------|
| `brazilian_soccer_mcp [--data-dir <path>]` | Loads CSVs (default `data/kaggle`), serves MCP on stdin/stdout; logs to stderr |
| `--help` / `-h` | Usage message |

## Data schema (in-memory)

`Match`: date (ISO), season (int), competition (canonical), round, home/away (`TeamName`), home_goals, away_goals, source.

`Player`: id, name, age, nationality, overall, potential, club, position, jersey_number, preferred_foot, value.

`TeamName`: display, base (accent-folded, no state), state. Identity key = `base-state` (e.g. `flamengo-rj`).

Source CSVs (6): Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro (matches); fifa_data (players).
