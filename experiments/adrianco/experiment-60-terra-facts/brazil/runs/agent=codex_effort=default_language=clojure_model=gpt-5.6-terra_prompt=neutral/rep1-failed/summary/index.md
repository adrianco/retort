# Summary: agent=codex model=gpt-5.6-terra language=clojure prompt=neutral · rep 1

- **Shape:** Clojure stdio MCP JSON-RPC server over in-memory CSV data (only dep: `org.clojure/data.json`), self-contained CSV reader.
- **Structure:** 3 source modules + 2 test files; 6 MCP tools; 5 `deftest` blocks / 15 assertions (all pass, test_coverage=1.0).
- **Interfaces:** 6 MCP tools (search_matches, team_stats, head_to_head, search_players, standings, dataset_statistics); 2 CLI aliases (`:run`, `:test`).
- **Notable:** Compact, idiomatic implementation with real accent/state-suffix normalization (`team-key`) — but `standings` groups by raw team name instead of that key, so name variants split the 2019 Série A table into 21 rows (the sole factual-gate failure, factual_accuracy=0.5). No cross-file dedup (23,954 rows = sum of 5 files).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
