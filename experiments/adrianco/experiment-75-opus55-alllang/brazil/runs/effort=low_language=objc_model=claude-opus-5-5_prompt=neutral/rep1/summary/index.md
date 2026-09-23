# Summary: effort=low_language=objc_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Objective-C / Foundation MCP server (JSON-RPC 2.0 over stdio) with an in-memory CSV knowledge base, ARC, no third-party dependencies.
- **Structure:** 8 source modules (7 `.m` libs + `main.m`) + 1 BDD test file; built with a hand-written Makefile.
- **Interfaces:** 4 MCP JSON-RPC methods + 15 tools; also a one-shot CLI mode. No HTTP.
- **Notable:** De-duplicates 5 overlapping match CSVs into 17,131 unique matches; standings/stats computed on demand from results; handles Brazilian team-name and date-format variants and UTF-8 accents. README candidly documents FIFA-19 data gaps (no Flamengo/Gabigol entries).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
