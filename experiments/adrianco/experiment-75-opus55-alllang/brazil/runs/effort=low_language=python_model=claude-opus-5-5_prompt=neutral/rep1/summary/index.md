# Architecture Summary

Dependency-free Python MCP server over the Brazilian soccer datasets. Two modules + a test suite.

## Modules

- **`soccer_data.py`** (462 lines) — data + query engine.
  - `SoccerDB` loads all 6 CSVs from `data/kaggle/` (`_read` with `utf-8-sig`), normalizes team names (`normalize_team`: accent stripping, state-suffix handling, alias table, rivalry/display maps), parses multiple date formats (`parse_date`), and dedupes overlapping match sources (`_dedupe`, ±3-day window keyed on competition/teams).
  - `Match` dataclass carries canonical keys + display names; `record()` aggregates W/D/L and goals.
  - Query surface: `find_matches` (team/venue/opponent/competition/season/date-range/round), `team_stats`, `head_to_head`, `standings` (computed table), `rankings`, `aggregate`, `biggest_wins`, `derbies`, `competitions_for`, `search_players` (name/nationality/club/position/min-overall), `brazilian_club_players`, `club_profile` (cross-file: FIFA players + match record).
  - `get_db()` is an `lru_cache`d singleton preloading data once.

- **`mcp_server.py`** (208 lines) — MCP stdio transport.
  - Hand-rolled JSON-RPC 2.0 over stdin/stdout (protocol `2024-11-05`), no SDK dependency.
  - `handle()` dispatches `initialize` / `ping` / `tools/list` / `tools/call`; notifications (no id) return `None`; unknown methods → `-32601`, parse errors → `-32700`, tool exceptions reported in-band via `isError`.
  - `TOOLS` registry maps 12 tools → (fn, description, inputSchema properties, required). Thin `t_*` wrappers format engine results into human-readable text.

## Interfaces

- Entry point: `python3 mcp_server.py` (stdio server). Client config example in README.
- Test entry: `python3 -m pytest tests`.

## Data flow

stdin JSON-RPC → `handle` → `call_tool` (arg filtering) → `t_*` wrapper → `SoccerDB` query → formatted text → stdout JSON-RPC.

*(Generated inline during evaluation; the `run-summary` skill was not invoked separately to stay within the time budget — the codebase is small enough to summarize directly.)*
