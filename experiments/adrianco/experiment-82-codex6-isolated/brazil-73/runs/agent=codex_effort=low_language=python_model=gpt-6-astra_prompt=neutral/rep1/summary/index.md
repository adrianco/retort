# Summary: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 1

- **Shape:** Standard-library Python MCP stdio server over an in-memory soccer knowledge graph built from six Kaggle CSVs (no MCP SDK, no pandas).
- **Structure:** 2 source modules + 1 test module (15 tests across 2 classes), 1 sample-questions data file.
- **Interfaces:** 11 MCP tools (search_matches, team_statistics, head_to_head, search_players, standings, analysis, team_profile, competition_bracket, derbies, graph_neighbors, coverage); full JSON-RPC handshake/discovery/error handling.
- **Notable:** Unusually complete for effort=low — cross-source deduplication with time-zone-aware fixture merging, team-name alias/state-suffix normalization, computed standings verified against the real 2019 Brasileirão (Flamengo 90 pts), a typed graph layer, and a real-subprocess stdio protocol test. Extremely dense one-line coding style. Stdlib-only (zero dependencies).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
