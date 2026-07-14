# Interfaces

## MCP / JSON-RPC methods (`mcp.clj:handle-request`)

| Method | Returns | Notes |
|--------|---------|-------|
| `initialize` | protocolVersion, capabilities, serverInfo | handshake |
| `ping` | `{}` | |
| `tools/list` | `{:tools [...]}` | name/description/inputSchema for each tool |
| `tools/call` | MCP tool result (`:content`, `:structuredContent`, `:isError`) | dispatches by tool name |
| (notifications, no `:id`) | nil | not answered, per JSON-RPC |
| (unknown method) | error `-32601` | |

## MCP tools (`mcp.clj:tools`)

| Tool | Purpose | Backed by |
|------|---------|-----------|
| `find_matches` | matches by team/opponent/venue/competition/season/date; h2h when team+opponent given | `query/find-matches`, `query/head-to-head` |
| `team_record` | W/D/L, goals, points for a team (season/competition/venue filters) | `query/team-record` |
| `head_to_head` | head-to-head record between two teams | `query/head-to-head` |
| `search_players` | FIFA players by name/nationality/club/position/min-overall | `query/search-players` |
| `brazilian_players_by_club` | Brazilian players grouped by Brazilian club w/ avg rating | `query/players-by-brazilian-club` |
| `standings` | league table for competition+season from match results | `query/standings` |
| `biggest_wins` | largest-margin victories | `query/biggest-wins` |
| `match_statistics` | total/avg goals, home/away/draw win rates | `query/summary-stats` |
| `best_record` | teams ranked by win rate (venue filter) | `query/best-record` |
| `list_competitions` | competitions with season coverage and match counts | `query/list-competitions` |

## Transport

Newline-delimited JSON-RPC 2.0 over stdio (`mcp.clj:serve!`). Protocol JSON to stdout; logs to stderr (`main.clj`). Protocol version `2024-11-05`.

## Data schema (in-memory knowledge graph, `data.clj:load-graph`)

- `:matches` — vector of canonical match maps: `:competition :season :date :round :stage :source :home :home-key :away :away-key :home-goal :away-goal :result`. Deduplicated on `[competition season home-key away-key]` across overlapping sources.
- `:players` — vector of FIFA player maps: `:id :name :age :nationality :overall :potential :club :club-key :position :name-key :nat-key`, …
- `:teams` — `{team-key {:key :name}}` node table (most-common display name per key).
- `:by-team` — `{team-key [match …]}` adjacency index.

Source CSVs (all under `data/kaggle/`): `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`.

## CLI

`clojure -M:run` starts the server; `clojure -M:test` runs the suite (`deps.edn` aliases).
