# Summary: effort=high · language=python · model=claude-opus-5-5 · prompt=atdd-skill · rep 2

- **Shape:** Python MCP (stdio) server over in-memory CSV data — a `brazilian_soccer_mcp` package with a thin tool layer (`server.py`) over one query engine (`knowledge.py`) and name/date/competition normalization helpers.
- **Structure:** 8 source modules (6 substantive) + a layered ATDD test suite — 7 acceptance spec files (52 tests) built on a DSL + protocol-driver stack, plus 2 unit test files (10 tests).
- **Interfaces:** 0 HTTP routes, 17 MCP tools, 1 CLI entry (`python -m brazilian_soccer_mcp --data-dir`); `SoccerKnowledge` exposes a matching library API returning `Answer(text, data)`.
- **Notable:** Unusually thorough data-quality handling — a dedicated `TeamRegistry` that parses inconsistent club names (state suffixes, country codes, aliases, accents) into stable keys, cross-dataset match de-duplication/merging, multi-format date parsing, and a 19-entry rivalry table. The test suite is a textbook four-layer ATDD build (specs → DSL → protocol drivers → system), with a hand-rolled MCP stdio client so tests exercise the real wire protocol, and per-test functional isolation via private data dirs.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
