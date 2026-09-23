# Architecture Summary — brazilian-soccer-mcp (C++17)

A self-contained MCP (Model Context Protocol) server over six Kaggle Brazilian-soccer
CSVs. No third-party libraries — a hand-written JSON layer and CSV parser keep the build
to the standard library only. Built with CMake as a `soccer` static lib + `brazilian_soccer_mcp`
executable + `soccer_tests`.

## Modules

| File | Lines | Responsibility |
|------|------:|----------------|
| `src/soccer.hpp` | 118 | Domain model: `Match`, `Player`, `Record`, `MatchFilter`, `Database` API |
| `src/text.cpp` | 217 | Accent stripping, text/team-name normalization, date normalization, competition canonicalization, CSV parsing |
| `src/loader.cpp` | 307 | Per-file CSV loaders for all 6 datasets; match de-duplication across overlapping sources |
| `src/queries.cpp` | 719 | Query engine + formatted answers: matches, team records, standings, players, head-to-head, rankings, derbies, profiles |
| `src/json.hpp` / `src/json.cpp` | 63 / 182 | Minimal JSON value type, parser and serializer |
| `src/mcp.cpp` / `src/mcp.hpp` | 223 / 17 | JSON-RPC 2.0 dispatch (`initialize`, `tools/list`, `tools/call`), 14 tool definitions |
| `src/main.cpp` | 32 | stdio JSON-RPC loop entrypoint |
| `tests/test_main.cpp` | 301 | 33 BDD-style scenarios, 107 assertions, loads the real CSVs via `DATA_DIR` |

## Data flow

`main` → `Database::loadDirectory(data/kaggle)` loads 6 CSVs (season-labelled sources
first, so cross-source fixtures de-dup by competition+teams+season/±4 days) → JSON-RPC
requests on stdin dispatched by `mcp::handle` → `mcp::callTool` maps tool name + arguments
to a `Database::fmt*` method → formatted text returned as MCP tool content.

## Notable design points

- **14 MCP tools** exposed (spec's 5 capability categories cover matches, teams, players,
  competitions, statistics; the extra tools are enhancements — derbies, team_profile,
  compare_seasons, team_rankings, biggest_wins, dataset_info).
- **Standings and head-to-head are computed** from raw match rows, not hardcoded.
- **Team-name normalization** collapses state suffixes ("Palmeiras-SP"→"Palmeiras"), full
  names ("Sport Club Corinthians Paulista"→"Corinthians") and accents to a canonical key.
- **Multi-format date parsing** (ISO, Brazilian DD/MM/YYYY, datetime-with-time).
