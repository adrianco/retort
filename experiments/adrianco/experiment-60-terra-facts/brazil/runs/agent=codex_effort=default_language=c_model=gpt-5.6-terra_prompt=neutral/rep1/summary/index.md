# Architecture summary

`run-summary` skill not available in this session — brief hand-written summary below.

Dependency-free C17 MCP server, three source files:

- **soccer.h** — data model (`Match`, `Player`, `SoccerDb`, `MatchFilter`, `Record`,
  `AggregateStats`) and the query API.
- **soccer.c** — CSV loader (RFC-4180-ish `csv_fields`), name normalization
  (`soccer_normalize` handles UTF-8 accents + state-suffix stripping via `team_key`),
  and the six query engines: `soccer_find_matches`, `soccer_team_record`,
  `soccer_head_to_head`, `soccer_find_players`, `soccer_standings`,
  `soccer_aggregate_stats`. A `is_canonical_for_aggregate` gate picks one source file
  per competition/season to avoid double-counting the overlapping datasets — the fix
  for the prior attempt's dedup failure.
- **main.c** — JSON-RPC-over-stdio loop; hand-rolled scalar JSON extractor (`value`),
  `tools/list` (6 tools), `resources/list`, and `tools/call` dispatch.

Data flows: startup loads 5 match CSVs + fifa_data.csv into memory (23k+ matches,
18,207 players), then each JSON-RPC request is answered from RAM.

Tests: `tests/test_soccer.c` (unit, exercises all query functions incl. the 2019
standings = 20 clubs / 38 played assertions) and `tests/test_mcp.sh` (black-box
protocol test over the built binary). Both run green (test_coverage=1.0).
