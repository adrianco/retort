# Summary: agent=codex effort=default language=rust model=gpt-5.6-sol prompt=neutral · rep 3

- **Shape:** Rust MCP server (JSON-RPC 2.0 over stdio, no framework) over 6 bundled Kaggle CSVs, with an in-memory query engine using the `csv`, `serde`, and `chrono` crates.
- **Structure:** 6 source modules + 1 integration test file (~1,579 LOC); 10 integration tests plus 5 embedded unit tests.
- **Interfaces:** 4 JSON-RPC methods, 8 MCP tools (match search, team stats, head-to-head, player search, standings, competition stats, biggest wins, cross-file team overview); library API on `SoccerStore` / `McpServer`; a `--check` CLI mode.
- **Notable:** This is a REPAIR run — the prior attempt failed on inflated standings from duplicate fixtures and broken team-name normalization. The fix adds a ±1-day fixture-dedup index (`FixtureKey` over canonical keys) and a disambiguating alias table that merges true variants (Corinthians, Bahia, Fortaleza) while keeping same-name clubs distinct (América-MG vs -RN, Botafogo-RJ vs -PB, Atlético-MG vs Athletico-PR). Tests hard-assert Flamengo's 2019 Série A 38-game / 90-point / 28-6-4 record and a 20-club table.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
