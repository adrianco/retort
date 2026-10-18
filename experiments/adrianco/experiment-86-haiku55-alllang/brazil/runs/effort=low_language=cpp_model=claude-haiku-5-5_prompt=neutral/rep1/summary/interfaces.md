# Interfaces

## MCP server (JSON-RPC 2.0 over stdio)

Protocol version `2024-11-05`; server `brazilian-soccer-mcp` v1.0.0.

| Method | Purpose |
|--------|---------|
| `initialize` | Returns protocolVersion, capabilities (`tools`), serverInfo |
| `ping` | Empty object |
| `tools/list` | Lists the 6 tools below with JSON-Schema input |
| `tools/call` | Dispatches a named tool with `arguments`, returns `content[]` text |

## MCP tools

| Tool | Arguments | Returns |
|------|-----------|---------|
| `find_matches` | team, opponent, competition, season, stage, date_from, date_to, venue, limit | Matches, most recent first |
| `team_record` | team (req), competition, season, venue | W/D/L, goals for/against, win rate |
| `head_to_head` | team (req), opponent (req), competition | H2H W/D/L, goals, recent meetings |
| `standings` | competition, season (req) | League table computed from matches (3/1/0 pts) |
| `search_players` | name, nationality, club, position, min_overall, limit | FIFA players, highest overall first |
| `goal_statistics` | team, competition, season | Avg goals/match, home/draw/away rates, biggest wins |

## Library API (namespace `soccer`)

- `Dataset::load(dataDir)` → `Dataset` with `matches()` / `players()`.
- Query functions in `queries.hpp`: `findMatches`, `teamRecord`, `headToHead`, `standings`, `searchPlayers`, `goalStats`, `displayTeamName`.
- `Json` value type with `parse` / `dump`.

## Data schema

- `Match`: date, season, competition, competitionKey, stage, home, away, homeKey, awayKey, homeGoals, awayGoals.
- `Player`: id, name, age, nationality, overall, potential, club, position, jerseyNumber, value, wage.

## CLI

`brazilian_soccer_mcp [data_dir]` — data dir from arg, else `$SOCCER_DATA_DIR`, else `data/kaggle`.
