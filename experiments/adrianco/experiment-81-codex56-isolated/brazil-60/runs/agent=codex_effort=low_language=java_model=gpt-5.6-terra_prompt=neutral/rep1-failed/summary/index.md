# Summary: agent=codex effort=low language=java model=gpt-5.6-terra prompt=neutral · rep 1

- **Shape:** Dependency-free Java 17 MCP stdio server (hand-rolled JSON-RPC + CSV + JSON) over an in-memory CSV repository.
- **Structure:** 7 main modules, 1 test file (6 JUnit 5 methods); 134 main LOC, ~14 test LOC; only test-scope dependency is JUnit.
- **Interfaces:** 6 MCP tools (search_matches, team_statistics, head_to_head, search_players, standings, competition_statistics); no HTTP/CLI.
- **Notable:** Very terse one-statement-per-line style. Server answers `initialize` but crashes (NPE from `Map.of(...,"id",null)`) on the required `notifications/initialized` notification and on any error input, so a real MCP handshake never completes — despite all 6 unit tests passing, because they bypass the transport.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
