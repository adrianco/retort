# Summary: effort=low_language=python_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Hand-rolled MCP server (stdio, JSON-RPC 2.0, no SDK) over a stdlib-`csv` knowledge base of 6 Brazilian-soccer datasets.
- **Structure:** 3 source modules (`server.py`, `soccer_data.py`, `test_soccer.py`), 1 test file, 977 non-test LOC + 218 test LOC.
- **Interfaces:** 0 HTTP routes / 0 CLI commands / 20 MCP tools + 4 lifecycle methods.
- **Notable:** No third-party deps at all (no `mcp` SDK, no pandas); eager in-memory load; results returned as preformatted text. Ships 20 tools — well beyond the 12 pinned requirements (derbies, brackets, cross-dataset `team_profile`). Heaviest logic is team-name normalization and multi-source match dedupe.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
