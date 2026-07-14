# Summary: language=go · model=sonnet-5 · prompt=none · rep 1

- **Shape:** Go stdlib-only MCP server (hand-rolled JSON-RPC 2.0 over stdio) over an in-memory store built from 6 Kaggle CSVs.
- **Structure:** 9 source modules + 5 test files (27 test functions); zero external dependencies.
- **Interfaces:** 6 MCP tools (search_matches, head_to_head, team_record, standings, stats_overview, search_players); no HTTP/CLI surface beyond stdio + `-data-dir` flag.
- **Notable:** Careful cross-source deduplication by season cutoff to avoid inflated aggregates; fuzzy accent/state-aware team-name resolution; standings verified against the real 2019 Brasileirão table.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
