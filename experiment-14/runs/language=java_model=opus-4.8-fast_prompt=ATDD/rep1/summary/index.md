# Architecture Summary

Brazilian Soccer MCP server in Java. A single Maven module (`com.brazilsoccer.mcp`),
built as a shaded jar (`Main` boots the server over stdio JSON-RPC).

## Modules

| File | Role |
|------|------|
| `Main.java` | Entry point; loads `data/kaggle`, wires `SoccerService` → `McpServer`, pumps stdin/stdout. |
| `McpServer.java` | JSON-RPC 2.0 MCP server: `initialize`, `tools/list`, `tools/call`, `ping`, notifications. Registers 6 tools with JSON input schemas via an inner `SchemaBuilder`. |
| `SoccerService.java` | Query layer. One `tool*` method per tool, each taking/returning Jackson `JsonNode` in domain language. |
| `DataStore.java` | Loads & de-duplicates the 6 CSVs (Apache Commons CSV); normalizes dates and goals; gates overlapping competition/season coverage to avoid double-counting league tables. |
| `TeamNames.java` | Team-name normalization (accents, state suffixes, identity keys). |
| `Competition.java` | Competition enum + label/key resolution. |
| `Match.java`, `Player.java` | Immutable row models. |

## Tools exposed (MCP surface)

`find_matches`, `head_to_head`, `team_stats`, `search_players`,
`competition_standings`, `league_statistics`.

## Data flow

`Main` → `SoccerService.load(dataDir)` → `DataStore.load` reads CSVs into
in-memory `List<Match>` / `List<Player>`. Each MCP `tools/call` dispatches to the
matching `SoccerService` method, which filters/aggregates the in-memory lists and
returns a JSON result wrapped in an MCP `content[].text` block.

## Test architecture (ATDD)

Acceptance tests drive the server **only** through `McpTestClient`, a JSON-RPC
client with no back-door access to internals — matching the ATDD prompt's
external-user / public-interface mandate. Unit-level `TeamNamesTest` covers the
normalization internals built underneath. 22 JUnit 5 tests, 0 skipped.
