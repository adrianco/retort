# Interfaces

## MCP methods (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | serverInfo, capabilities.tools, negotiated protocolVersion | `server.cpp:serve` (108) |
| `ping` | `{}` | `server.cpp:serve` (114) |
| `tools/list` | one tool: `query_soccer` (description embeds live schema) | `server.cpp:toolsList` (78) |
| `tools/call` | runs one read-only SELECT; `{columns, rows, truncated}` or `isError` | `server.cpp:query` (48) |
| notifications (no `id`) | silently dropped | `server.cpp:serve` (107) |

Unknown method → JSON-RPC error `-32601`; unknown tool → `-32602`; parse error → `-32700`; bad request → `-32600`.

## Tool: `query_soccer`

Input: `{ "sql": string }` — a single read-only SQLite `SELECT`. Guarded by an authorizer (SELECT/READ/RECURSIVE + an allow-list of scalar/aggregate/window functions only), a 4-second progress-handler deadline, length/SQL-length limits, and a 200-row cap with a `truncated` flag.

## Data schema (in-memory SQLite, built at startup from 6 CSVs)

Raw import tables: `league` (Brasileirão), `cup` (Copa do Brasil), `libertadores`, `historical` (2003–2019 Série A), `extended` (BR-Football stats), `players` (FIFA, 18,207 rows).

Derived:
- `matches(competition, season, date, home, away, home_goal, away_goal, round, stage, source)` — unified, team-normalized fixtures across Série A / Copa do Brasil / Libertadores, deduped and score-reconciled against `extended`; cup `stage='final'` tagged heuristically.
- `performances(competition, season, date, team, opponent, venue, gf, ga)` — one row per team per scored fixture.
- `standings(competition, season, team, played, wins, draws, losses, goals_for, goals_against, gd, points)` — 3-1-0 points, computed from `performances`.
- `rivals(a,b)` + `derbies` view — selected traditional rivalries.

Normalization UDFs: `team(name)` (accent-fold + state-suffix/alias canonicalization), `fold(name)` (accent-insensitive).
