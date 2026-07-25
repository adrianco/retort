# Architecture Summary

> The `run-summary` skill is not wired into this evaluation session's Skill tool, so
> this is a concise hand-written architecture note in its place.

## Modules (`src/main/java/com/brsoccer/mcp/`)

| Package | File | Responsibility |
|---------|------|----------------|
| `.` | `Main.java` | Entry point. Resolves data dir (arg / `$BRSOCCER_DATA` / `./data/kaggle`), loads the datasets, serves MCP over stdio. |
| `server` | `McpServer.java` | Minimal MCP server — newline-delimited JSON-RPC 2.0 over stdin/stdout. Handles `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`, notifications. |
| `tools` | `McpTools.java` | Declares 9 MCP tools (name + JSON schema + description) and formats each tool's text result. Dispatches `tools/call` to `QueryService`. |
| `query` | `QueryService.java` | Typed query layer: `findMatches`, `headToHead`, `teamStats`, `standings`, `searchPlayers`, `aggregate`, `biggestWins`, `rankings`. Uses records for result types. |
| `data` | `DataStore.java` | Loads all 6 CSVs, normalizes competitions, de-duplicates fixtures across files (±1 day key). |
| `data` | `TeamRegistry.java` | Team-name normalization (strips `-SP` suffixes, accents) → canonical keys, plus display names. |
| `model` | `Match.java`, `Player.java` | Domain records/POJOs. |

## Flow

`Main` → `DataStore.loadAll()` (6 CSVs → in-memory, de-duplicated) → `QueryService(store)` →
`McpTools(query)` → `McpServer.run()` reads JSON-RPC lines from stdin, routes `tools/call`
to `McpTools.call(name, args)` → `QueryService` → formatted text back over stdout.

## Tools exposed

`search_matches`, `head_to_head`, `team_stats`, `league_standings`, `search_players`,
`player_info`, `competition_stats`, `team_rankings`, `list_competitions`.

## Tests (`src/test/.../mcp/`)

`DataStoreTest` (4), `McpServerTest` (7), `QueryServiceTest` (19), `TeamRegistryTest` (9),
`SampleQuestionsTest` (1 parameterized test × 24 rows). All assert real values; 0 skips.
