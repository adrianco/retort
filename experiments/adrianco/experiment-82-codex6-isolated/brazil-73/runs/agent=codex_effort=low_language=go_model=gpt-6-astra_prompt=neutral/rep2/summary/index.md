# Summary: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 2

- **Shape:** Go stdio MCP server (hand-rolled JSON-RPC 2.0, no SDK) over an in-memory store loaded from six Brazilian soccer CSVs.
- **Structure:** 4 source modules (~898 non-blank src lines), 1 test file (7 test functions), no third-party dependencies.
- **Interfaces:** 8 MCP tools (search_matches, search_players, team_profile, head_to_head, standings, statistics, competition_results, data_info); 1 CLI entrypoint.
- **Notable:** strong normalization/dedup across heterogeneous CSVs (accent folding, team aliases, cross-source merge with conflict warnings, season inference); strict JSON decoding; 92% test coverage incl. a real-dataset integration test asserting exact 2019 Série A standings.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
