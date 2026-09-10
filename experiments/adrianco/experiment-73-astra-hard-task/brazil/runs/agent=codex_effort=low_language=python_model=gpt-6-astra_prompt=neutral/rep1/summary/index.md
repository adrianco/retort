# Summary: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 1

- **Shape:** Dependency-free Python MCP stdio server over an in-memory Brazilian-soccer knowledge graph built from six Kaggle CSVs.
- **Structure:** 3 source modules (`soccer.py`, `server.py`, `build.py`) + 1 test file (20 tests) + a 28-entry sample-questions fixture.
- **Interfaces:** 13 MCP tools; full JSON-RPC lifecycle (initialize/initialized/tools.list/tools.call/ping); CLI `server.py --data-dir` and a `build.py` zipapp packager.
- **Notable:** Stdlib-only (zero deps); tool JSON schemas auto-derived from method signatures via `inspect`; cross-source match deduplication with provenance retained; team-name normalization with alias table and state-suffix disambiguation for homonymous clubs.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
