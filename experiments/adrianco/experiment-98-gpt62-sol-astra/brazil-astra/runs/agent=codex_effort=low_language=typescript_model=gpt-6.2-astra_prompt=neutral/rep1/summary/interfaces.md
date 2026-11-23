# Interfaces

## MCP transport (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion, capabilities.tools, serverInfo, instructions | `server.ts:respond` |
| ping | `{}` | `server.ts:respond` |
| tools/list | `{ tools }` (4 tools) | `server.ts:respond` |
| tools/call | `{ content: [{type:"text", text: JSON}] }` or `{ isError, content }` | `server.ts:respond` → `queries.ts:query` |

Notifications (requests without `id`) are accepted and produce no reply. Parse errors → -32700, invalid request → -32600, unknown method → -32601, missing tool name → -32602.

## MCP tools (queries.ts)

| Tool | Purpose | Key args |
|------|---------|----------|
| matches | Fixture search; latest/earliest/biggest_win ordering; derby & knockout filters | team, opponent, venue, competition, season, from, to, stage, round, derby, source, order, played, limit, offset |
| records | Team / head-to-head / league-standings records | team, opponent, venue, competition, season, sort(points\|goals\|win_rate), limit, offset |
| statistics | Aggregate goals, home/away win counts; group by all/season/competition | team, competition, season, from, to, group |
| players | FIFA player search | name, club, nationality, position, details, limit, offset |

## Data schema

- `Match`: id, date, season, competition, home, away, homeGoals, awayGoals, round, stage, sources[], details(raw row).
- Player rows: raw FIFA CSV columns (ID, Name, Age, Nationality, Overall, Potential, Club, Position, skill attributes, …).
- Datasets loaded from `data/kaggle/`: Brasileirao_Matches, novo_campeonato_brasileiro, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, fifa_data.

## Data schema notes

Cross-source match dedup: fixtures keyed by (competition, season, home, away) are merged across the overlapping Serie A sources so the 2019 league table counts each fixture once (38 matches/team).
