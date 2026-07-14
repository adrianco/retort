# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdin/stdout)

| Method | Handler | Returns |
|--------|---------|---------|
| `initialize` | `core.clj:handle-request` | protocolVersion / capabilities / serverInfo |
| `notifications/initialized` | `core.clj:handle-request` | (no response) |
| `tools/list` | `core.clj:handle-request` | the 6 tool schemas |
| `tools/call` | `core.clj:handle-call` | `{:content [{:type "text" :text <json>}]}` |

## MCP tools (registered in `tool-schemas`)

| Tool | Args | Handler |
|------|------|---------|
| find-matches | team / team1 / team2 / competition / season / date-from / date-to / limit | `tools/find-matches` |
| get-team-stats | team (req) / competition / season / venue | `tools/get-team-stats` |
| find-players | name / nationality / club / position / min-overall / sort-by / limit | `tools/find-players` |
| get-head-to-head | team1 (req) / team2 (req) / competition / season | `tools/get-head-to-head` |
| get-standings | season (req) / competition | `tools/get-standings` |
| get-statistics | stat-type (req) / competition / season / limit | `tools/get-statistics` |

## Data schema (in-memory, from `load-all-data`)

`{:brasileirao-matches :cup-matches :libertadores-matches :br-football :historical-brasileirao :fifa-players}`.
Match records: `{:home-team :away-team :home-goal :away-goal :date :season :competition ...}`.
Player records: `{:id :name :age :nationality :overall :potential :club :position ...}`.
