# Summary: language=clojure_model=opus-4.8-fast_prompt=ATDD · rep 1

- **Shape:** Clojure MCP server (JSON-RPC 2.0 over stdio) over an in-memory model built from the Kaggle Brazilian-soccer CSVs; 4 source namespaces + 3 test namespaces.
- **Structure:** 4 modules (~690 LoC src), 4 test files (~377 LoC, 20 deftests / 76 assertions).
- **Interfaces:** 5 JSON-RPC methods, 6 MCP tools (find_matches, team_stats, compare_teams, search_players, competition_standings, competition_stats); 2 normalized data schemas.
- **Notable:** Clean ATDD layering — acceptance tests drive the protocol through `process-line` only (no back-door), with a unit-TDD normalization layer beneath. Eager full-dataset load + linear-scan queries; cross-file dedup by (competition, season). Thorough team-name normalization (accents, state/country suffixes) and multi-format date/goal parsing.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
