# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2024-11-05`, capabilities, serverInfo | `core.clj:handle-message` |
| `tools/list` | `{tools: [...]}` (7 tool definitions) | `core.clj:handle-message` |
| `tools/call` | `{content:[{type:"text",text}], isError}` | `core.clj:handle-message` → `tools/call-tool` |

Notifications (no `id`) are accepted and produce no response. Unknown methods return JSON-RPC error `-32601`; parse failures return `-32700`.

## MCP tools

| Tool | Required args | Optional args | Backing fn |
|------|---------------|---------------|------------|
| `search_matches` | (none) | team, opponent, competition, season, date_from, date_to, limit | `tools/search-matches` |
| `get_team_stats` | team | competition, season, venue | `tools/get-team-stats` |
| `search_players` | (none) | name, nationality, club, min_overall, max_overall, position, limit | `tools/search-players` |
| `get_standings` | season | competition | `tools/get-standings` |
| `get_head_to_head` | team1, team2 | competition, season, limit | `tools/get-head-to-head` |
| `get_biggest_wins` | (none) | team, competition, season, limit | `tools/get-biggest-wins` |
| `get_competition_stats` | (none) | competition, season | `tools/get-competition-stats` |

Tool results are returned as preformatted human-readable text, not structured JSON.

## Data schema (in-memory, loaded from `data/kaggle/`)

- **Match** (normalized across 5 datasets): `:date` (ISO string), `:home-team`, `:away-team`, `:home-goals`, `:away-goals`, `:season`, `:competition` (keyword), `:round`/`:stage`/`:tournament`. BR-Football rows add `:home-corners`/`:away-corners`/`:home-shots`/`:away-shots`.
- **Player** (FIFA): `:id`, `:name`, `:age`, `:nationality`, `:overall`, `:potential`, `:club`, `:position`, `:jersey-number`, `:height`, `:weight`, `:value`, `:wage`.

## CLI commands

(none — server is driven entirely via stdin JSON-RPC)
