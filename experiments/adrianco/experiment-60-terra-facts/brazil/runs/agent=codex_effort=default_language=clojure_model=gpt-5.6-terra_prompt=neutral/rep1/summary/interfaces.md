# Interfaces

## MCP tools (JSON-RPC over stdio)

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout. Methods handled:
`initialize`, `tools/list`, `tools/call`. Unknown methods → `-32601`.

| Tool | Inputs | Returns | Handler |
|------|--------|---------|---------|
| search_matches | team, team-a, team-b, competition, season, from, to, limit | `[match]` (date-desc, ≤500) | `core/search-matches` |
| team_stats | team*, competition, season, venue (home/away) | W/L/D, goals-for/against, win-rate | `core/team-stats` |
| head_to_head | team-a*, team-b*, competition, season | a-wins/b-wins/draws + recent 20 | `core/head-to-head` |
| search_players | name, nationality, club, position, limit | `[player]` (overall-desc, ≤500) | `core/search-players` |
| standings | season*, competition | table sorted by pts, GD, GF | `core/standings` |
| dataset_statistics | competition, season | match count, avg goals/match, home/draw/away wins | `core/dataset-statistics` |

`*` = required per `inputSchema`. Every tool result is returned both as MCP text
content (`json/write-str`) and as `:structuredContent`.

## Data schema (in-memory, built at startup)

- **match**: `{:competition :date :season :round/:stage :home :away :home-key :away-key :home-goals :away-goals ...}` — concatenation of 5 CSVs (Brasileirão, Copa do Brasil, Libertadores, extended BR-Football, historical novo_campeonato), 23,954 rows.
- **player**: `{:id :name :age :nationality :overall :potential :club :position :name-key :club-key}` — from fifa_data.csv, 18,207 rows.
- Team matching key `team-key`: NFD-fold accents, lower-case, strip trailing `-XX` state suffix and common club-type words.

## CLI

- `clojure -M:run` → starts the stdio MCP server (`server/-main`).
- `clojure -M:test` → runs the test suite (`test-runner/-main`).
