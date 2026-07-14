# Summary: language=go · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** Go stdlib-only MCP server (JSON-RPC 2.0 over stdio) over an in-memory store loaded from 6 Kaggle CSVs.
- **Structure:** 9 source modules, 6 test files (42 test functions, all BDD `Given/When/Then`-named).
- **Interfaces:** 10 MCP tools spanning match/team/player/competition/statistics queries; 1 CLI flag; no HTTP.
- **Notable:** Zero third-party dependencies. Deduplicates overlapping Brasileirão fixtures across source files; curated team-name normalization distinguishes identity-bearing suffixes (Atlético-MG) from decorative ones (Palmeiras-SP). Integration tests pin real-data invariants (2019 Brasileirão = 90 pts / 38 matches).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
