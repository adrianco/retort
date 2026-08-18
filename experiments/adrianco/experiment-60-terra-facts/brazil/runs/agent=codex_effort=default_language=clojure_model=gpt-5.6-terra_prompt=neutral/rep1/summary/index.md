# Summary: agent=codex model=gpt-5.6-terra language=clojure prompt=neutral · rep 1

- **Shape:** Clojure stdio MCP JSON-RPC server over in-memory CSV data (only dep: `org.clojure/data.json`), self-contained CSV reader.
- **Structure:** 3 source modules + 2 test files; 6 MCP tools; 6 `deftest` blocks / 20 assertions (all pass, test_coverage=1.0).
- **Interfaces:** 6 MCP tools (search_matches, team_stats, head_to_head, search_players, standings, dataset_statistics); 2 CLI aliases (`:run`, `:test`).
- **Notable:** Compact, idiomatic implementation with real accent/state-suffix normalization (`team-key`). `standings` correctly groups by the canonical `:home-key`/`:away-key` **and** de-dups via `unique-fixtures` — the archived server returns a correct 20-team 2019 Série A table (Flamengo 90 pts, Athletico merged). The stored `factual_accuracy=0.5` (21 rows) is a stale false-negative from a pre-fix probe; see `evaluation.md`. **Real defect:** `team_stats`/`head_to_head` do NOT apply that dedup, so records double-count fixtures shared across the 5 match files (Flamengo 2019 → 76 games, 2x the real 38).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
