# Architecture Summary — Brazilian Soccer MCP Server (C)

Dependency-free C11. `make` → `bin/brsoccer-mcp`, a JSON-RPC 2.0 stdio MCP server
(also `--call`/`--demo` for shell use). ~6.4K LOC C + ~1.1K LOC headers in `src/`,
~2.2K LOC of tests. No third-party libraries — CSV reader, JSON parser/writer,
hash maps and the transport are all hand-written.

## Modules (`src/`)

| Module | Responsibility |
|--------|----------------|
| `main.c` | Entry point; CLI dispatch (`--serve`, `--call`, `--demo`). |
| `mcp.c` / `mcp.h` | JSON-RPC 2.0 loop, MCP methods `initialize`/`ping`/`tools/list`/`tools/call`. |
| `tools.c` / `tools.h` | 14 tool definitions + invocation, each returning prose + `structuredContent`. |
| `query.c` / `query.h` | Analytical layer: match filtering, team records, head-to-head, standings, rankings, competition stats, player filtering, squads, season comparison. |
| `db.c` / `db.h` | Loads all 6 `data/kaggle/*.csv`, de-duplicates overlapping fixtures (42,161 rows → 16,779 matches), indexes teams/players. |
| `teams.c` / `teams.h` | 7-step club-name normalization pipeline + curated alias table. |
| `csv.c` / `csv.h` | Zero-copy CSV parser (handles BOM, quoting). |
| `json.c` / `json.h` | JSON parse + streaming writer. |
| `format.c` / `format.h` | Human-readable prose formatting of results. |
| `util.c` / `util.h` | String folding, date parsing (ISO + Brazilian formats), helpers. |
| `questions.h` | The 28 spec sample questions used by `--demo`. |

## MCP tools (14)

`search_matches`, `head_to_head`, `team_stats`, `team_profile`, `standings`,
`rank_teams`, `competition_stats`, `biggest_wins`, `search_players`,
`player_profile`, `club_squads`, `compare_seasons`, `list_teams`, `dataset_info`.

## Tests

`tests/*.c` are Given/When/Then suites mirroring the 8 `tests/features/*.feature`
Gherkin files. A shared, lazily-loaded `Db` is reused across suites. Result:
**93 scenarios, 460 checks, 0 failures**, clean under `-fsanitize=address,undefined`
and `-Wall -Wextra -Wpedantic -Wshadow` with zero warnings.
