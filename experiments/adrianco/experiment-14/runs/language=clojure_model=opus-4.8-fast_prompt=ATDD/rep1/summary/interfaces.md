# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

| Method | Returns | Handler |
|--------|---------|---------|
| `initialize` | protocolVersion `2024-11-05`, capabilities, serverInfo | `server.clj:handle-request` |
| `tools/list` | list of tool descriptors (sans handler) | `tools.clj:public-list` |
| `tools/call` | `{:content [{:type "text" :text ...}]}` or JSON-RPC error | `server.clj:handle-tools-call` |
| `ping` | `{}` | `server.clj:handle-request` |
| `notifications/*` | (no reply) | `server.clj:handle-request` |

## MCP tools

| Tool | Args | Purpose |
|------|------|---------|
| `find_matches` | team, opponent, competition, season, start_date, end_date, limit | Match listing + head-to-head when team+opponent given |
| `team_stats` | team*, season, competition, venue (home/away) | W/D/L, goals for/against, win rate |
| `compare_teams` | team1*, team2* | Head-to-head record + match list |
| `search_players` | name, nationality, club, position, limit | FIFA player search sorted by overall |
| `competition_standings` | competition*, season | League table computed from match results |
| `competition_stats` | competition, season | Avg goals/match, home/away win rate, biggest wins |

(* = required in inputSchema)

## Data schema (normalized in-memory model)

- **match**: `:competition :season :round :stage :date :home :away :home-display :away-display :home-norm :away-norm :home-key :away-key :home-goal :away-goal :source`
- **player**: `:id :name :age :nationality :overall :potential :club :position :jersey :name-norm :nat-norm :club-norm`

Source files read from `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro (matches); fifa_data (players). File kind is inferred from header columns.
