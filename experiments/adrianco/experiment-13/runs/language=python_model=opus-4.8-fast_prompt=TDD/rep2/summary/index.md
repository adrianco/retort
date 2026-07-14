# Summary: language=python · model=opus-4.8-fast · prompt=TDD · rep 2

- **Shape:** Python FastMCP (Model Context Protocol) server over Brazilian-soccer Kaggle CSVs, with a clean server → format → query → data-loader layering.
- **Structure:** 6 source modules (~1,131 LoC), 6 test files (~600 LoC, 60 test functions).
- **Interfaces:** 10 MCP tools (matches, head-to-head, team record, standings, players ×2, statistics, biggest wins, best record, data summary); no HTTP/CLI — MCP stdio transport.
- **Notable:** Strong separation of concerns makes query/format logic unit-testable without an MCP session; tolerant CSV parsing; season de-duplication across overlapping sources; official Brasileirão tiebreakers; integration tests assert real historical facts (2019 champion Flamengo on 90 pts). Consistent with the prescribed test-first (TDD) methodology — one focused unit-test file per module plus an end-to-end suite.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
