# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio, newline-delimited)

Hand-rolled MCP server (no Clojure MCP SDK exists). Methods handled in `server.clj:handle`:

| Method | Behavior |
|--------|----------|
| `initialize` | Returns `protocolVersion`, `capabilities.tools`, `serverInfo {name: "brazilian-soccer", version: "1.0.0"}` |
| `ping` | Empty result |
| `tools/list` | Returns 13 tool descriptors with JSON `inputSchema` |
| `tools/call` | Dispatches to the named tool handler; returns `{content: [{type: "text", text}]}` |
| unknown method | JSON-RPC error `-32601`; unknown tool → `-32602`; parse error → `-32700` |

## MCP tools (13)

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Find matches | team, opponent, competition, season, date_from, date_to, venue, limit |
| `head_to_head` | H2H record + match list between two teams | team, opponent (required) |
| `team_stats` | W/D/L + goals for a team | team (required), competition, season, venue |
| `standings` | Brasileirão league table computed from matches | season (required) |
| `top_scoring_teams` | Teams ranked by goals in a season | season (required) |
| `competition_stats` | Avg goals, home/away/draw rates, biggest wins | competition, season, team |
| `best_records` | Rank teams by win rate | venue, competition, season, min_matches |
| `team_competitions` | Competitions a team has played in | team (required) |
| `cup_finals` | Copa do Brasil / Libertadores finals | competition |
| `derbies` | Traditional rivalry matches | season, competition, team |
| `search_players` | FIFA player search | name, nationality, club, position |
| `brazilian_players_by_club` | Brazilian players grouped by club w/ avg rating | all_clubs |
| `player_profile` | Player FIFA info + club's match record (cross-file) | name (required) |

## Data schema (in-memory, from `load-all`)

- `:sources` → `{:brasileirao :cup :libertadores :br-football :historical}` (per-file vectors)
- `:matches` → concatenation of all match rows; each: `:date :season :home :away :home-goal :away-goal :home-key :away-key :competition :result (:home/:away/:draw)` plus optional `:round :stage :arena :stats`
- `:players` → FIFA rows: `:id :name :age :nationality :overall :potential :club :club-key :position :skills` …

Loaded from 6 CSVs in `data/kaggle/`: Brasileirao (4180), Cup (1337), Libertadores (1255), BR-Football (10296), historical (6886), fifa_data (18207 players).
