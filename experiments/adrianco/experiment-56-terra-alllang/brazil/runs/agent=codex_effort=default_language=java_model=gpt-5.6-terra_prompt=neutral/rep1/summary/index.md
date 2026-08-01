# Architecture Summary

Dependency-free Java 17 MCP stdio server over six Brazilian-soccer CSV files, loaded
into memory at startup. `run-summary` skill was unavailable; this summary was written
directly from the source (10 files, ~137 LOC).

## Modules

| Class | Role |
|-------|------|
| `Main` | Entry point; loads `data/kaggle` (or `args[0]`) and serves on stdin/stdout. |
| `McpServer` | JSON-RPC 2.0 / MCP `2024-11-05` dispatcher (`initialize`, `tools/list`, `tools/call`, `ping`). Registers 7 tools and maps arguments to `SoccerService`. |
| `SoccerService` | Query + aggregation layer: `findMatches`, `teamStats`, `headToHead`, `standings`, `findPlayers`, `biggestWins` plus result records (`TeamStats`, `HeadToHead`, `Standing`). |
| `SoccerRepository` | Loads/normalizes the 5 match CSVs + FIFA player CSV into immutable `List<Match>`/`List<Player>`; date parsing with multiple formats. |
| `TeamNames` | Accent/state-suffix/alias normalization for team-name matching. |
| `Match`, `Player`, `Standing`… | Immutable records. |
| `Csv`, `Json` | Hand-rolled CSV reader and JSON parser/writer (no dependencies). |
| `AcceptanceTest` | `main`-based Given/When/Then harness with 8 assertions; wired to `mvn test` via exec-maven-plugin. |

## Flow

`Main` → `SoccerRepository.load` → `SoccerService` → `McpServer.serve` reads NDJSON
lines, dispatches JSON-RPC, and returns MCP `content` + `structuredContent`. An `ask`
tool routes free-text (EN/PT) questions to the appropriate query.

## Tools exposed

`search_matches`, `team_statistics`, `head_to_head`, `standings`, `search_players`,
`biggest_wins`, `ask`.
