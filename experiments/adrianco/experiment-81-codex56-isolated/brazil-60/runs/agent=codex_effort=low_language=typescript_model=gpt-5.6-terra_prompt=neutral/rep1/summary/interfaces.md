# Interfaces

## MCP tools (JSON-RPC over stdio)

Transport is hand-rolled JSON-RPC 2.0 on stdin/stdout (not the official MCP SDK). `initialize` advertises `protocolVersion: 2024-11-05`; `tools/list` returns the six tools; `tools/call` dispatches by name. Every tool's `inputSchema` is `{type:"object", additionalProperties:true}` (no per-tool argument schema).

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| search_matches | team?, opponent?, competition?, season?, from?, to?, stage?, limit? | `{count, matches[], truncated}` | `service.ts:findMatches` |
| team_statistics | team (required), season?, competition?, venue? | `{team, matches, wins, draws, losses, goalsFor, goalsAgainst, points, winRate}` | `service.ts:teamStats` |
| compare_teams | teamA (required), teamB (required), filters | `{teamAWins, teamBWins, draws, recent[]}` | `service.ts:headToHead` |
| competition_standings | competition (required), season (required) | `[{team, played, wins, draws, losses, goalsFor, goalsAgainst, points, position}]` | `service.ts:standings` |
| search_players | name?, nationality?, club?, position?, limit? | `{count, players[], truncated}` | `service.ts:players` |
| competition_statistics | same filter as search_matches | `{matches, totalGoals, goalsPerMatch, homeWinRate, drawRate, biggestWins[]}` | `service.ts:aggregate` |

## Data schema (in-memory)

- `Match`: source, competition, date (ISO), season, round?, stage?, home, away, homeGoals, awayGoals, extras.
  Sources: `brasileirao`, `brazilian-cup`, `libertadores`, `extended` (BR-Football), `historical` (novo_campeonato).
- `Player`: id, name, age?, nationality, overall?, potential?, club, position, attributes.

## HTTP routes

(none)

## CLI commands

(none — server reads JSON-RPC requests from stdin)
