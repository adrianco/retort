# Summary: agent=codex effort=low model=gpt-6.2-astra prompt=neutral · rep 1

- **Shape:** Stdlib-only Python MCP server (newline-delimited JSON-RPC over stdio) backed by an in-memory soccer knowledge graph built from 6 Kaggle CSVs.
- **Structure:** 3 modules (soccer.py, server.py, test_soccer.py), 1 test file with 9 scenarios, no external dependencies.
- **Interfaces:** 3 MCP tools (`find_matches`, `find_players`, `statistics`) + 5 JSON-RPC methods (initialize/tools/list/tools/call/ping/errors); no HTTP/CLI.
- **Notable:** Dense, highly idiomatic code (413 LOC total). Sophisticated cross-dataset de-duplication of overlapping league fixtures and thorough team-name normalization (accents, state suffixes, aliases). Computes standings/head-to-head from raw matches; refuses to invent scores for unplayed fixtures.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
