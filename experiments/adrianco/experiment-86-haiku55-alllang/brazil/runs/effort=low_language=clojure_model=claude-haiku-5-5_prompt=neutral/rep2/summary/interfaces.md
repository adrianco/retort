# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| initialize | protocolVersion `2024-11-05`, capabilities.tools, serverInfo | `server.clj:dispatch` |
| ping | `{}` | `server.clj:dispatch` |
| tools/list | array of tool descriptors (name, description, inputSchema) | `tools.clj:tool-descriptors` |
| tools/call | `{content:[{type:"text", text}], isError}` | `server.clj:call-tool-result` → `tools.clj:call-tool` |

Unknown method → `-32601`; unknown tool → `-32602`; internal error → `-32603`; parse error → `-32700`; invalid request → `-32600`. Notifications (no `id`) get no response.

## MCP tools

| Tool | Purpose | Key args |
|------|---------|----------|
| search_matches | Find matches | team, opponent, competition, season, date_from, date_to, venue, limit |
| team_record | W/D/L + goals for/against | team (req), competition, season, venue |
| head_to_head | Head-to-head between two teams | team_a (req), team_b (req) |
| standings | Season league table (3/1/0 pts) computed from matches | season (req), competition |
| league_stats | goals/match, home/away/draw rates, biggest wins | competition, season, date_from, date_to |
| search_players | FIFA player search | name, nationality, club, position, min_overall, limit |
| brazilian_club_summary | Brazilian players grouped by club (count, avg overall) | (none) |

## Data schema (normalized in-memory)

Match: `{:date "yyyy-MM-dd" :season int :competition str :round str|nil :home str :away str :home-key str :away-key str :home-goals int :away-goals int :source str}`.

Player: `{:id :name :age :nationality :overall :potential :club :position :jersey-number}`.

Sources: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv` (used only for competition-seasons no primary file covers), `fifa_data.csv`.

## HTTP routes / CLI commands

(none — the only external surface is the MCP stdio server launched via `clojure -M:server [data-dir]`.)
