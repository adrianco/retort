# Architecture Summary — Brazilian Soccer MCP Server (Java)

## Surface
A standalone JVM application (`Main`) that loads the Kaggle CSV datasets from
`data/kaggle/` into an in-memory database and serves the **Model Context
Protocol** over **JSON-RPC 2.0** on stdio. Built with Maven; only two runtime
deps (`jackson-databind`, `junit-jupiter` for tests). 2,066 LOC main / 1,038 LOC
test across 32 source files.

## Modules

| Package | Files | Responsibility |
|---------|-------|----------------|
| `mcp` | `Main`, `McpServer`, `StdioTransport`, `SoccerTools`, `ToolDefinition` | Entry point, JSON-RPC dispatch (`initialize`, `tools/list`, `tools/call`), stdio framing, and the 7 MCP tool implementations. |
| `data` | `DataStore`, `DataLoader`, `Matches` | Loads all 6 CSVs (5 match files + FIFA players), tolerates missing columns/rows, dedups/cleans matches. |
| `csv` | `CsvParser`, `Dates` | RFC-style CSV parsing; multi-format date parsing (ISO, Brazilian `DD/MM/YYYY`, with-time). |
| `model` | `Match`, `Player`, `TeamNames` | Immutable records + team-name canonicalization (strips `-SP` suffixes, normalizes accents). |
| `query` | `SoccerDatabase`, `MatchQuery`, `PlayerQuery`, `HeadToHead`, `TeamRecord`, `StandingRow`, `Venue` | The query engine: match filtering, head-to-head, team records, computed standings, aggregate statistics. |

## Interfaces — MCP tools (7)

| Tool | Maps to |
|------|---------|
| `find_matches` | match search by team / venue / competition / season / date range |
| `head_to_head` | W/L/D between two teams |
| `team_record` | aggregated W/L/D + goals for a team (optional season/competition/venue) |
| `competition_standings` | points table computed from match results |
| `search_players` | FIFA player search by name / nationality / club / position / min rating |
| `match_statistics` | avg goals/match, home win rate, biggest wins |
| `list_competitions` | distinct competitions in the loaded data |

## Control flow
`Main` → `DataStore.loadFromDirectory(data/kaggle)` builds `SoccerDatabase` →
`McpServer` reads JSON-RPC requests via `StdioTransport` → dispatches `tools/call`
to `SoccerTools.call(name, args)` → parses args into a `MatchQuery`/`PlayerQuery`,
runs the `SoccerDatabase` query, and renders LLM-friendly text in the spec's
answer formats.
