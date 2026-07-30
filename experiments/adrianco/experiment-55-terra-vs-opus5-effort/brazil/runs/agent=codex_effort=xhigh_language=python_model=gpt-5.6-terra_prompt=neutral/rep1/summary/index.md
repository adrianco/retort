# Architecture Summary

Brazilian Soccer MCP server. Clean two-layer split: a pure query **service**
over the bundled CSVs, and a thin **MCP adapter** that exposes each service
method as a FastMCP tool. `run-summary` skill was not invocable in this
environment; this summary was written directly.

## Modules

| Module | Lines | Role |
|--------|-------|------|
| `soccer_mcp/service.py` | 948 | Core. `SoccerData` loads the 6 CSVs (cached via `lru_cache`) into `Match` dataclasses + player dicts, and implements every query: `search_matches`, `team_statistics`, `head_to_head`, `team_overview`, `competition_standings`, `competition_statistics`, `search_players`, `answer_question`, `data_summary`. |
| `soccer_mcp/normalization.py` | 104 | Accent/case/whitespace folding, team-name keys (state-suffix stripping + alias table), competition canonicalization, display formatting. |
| `soccer_mcp/server.py` | 103 | `create_mcp_server()` lazily imports FastMCP and registers 9 tools that delegate to `SoccerData`; `main()` runs stdio transport. |
| `soccer_mcp/build_backend.py` | 143 | Custom dependency-free PEP 517 backend (no setuptools) that bundles the CSVs into the wheel/sdist. |
| `tests/` | 160 | 15 tests: 14 service behaviour tests over the real datasets + 1 MCP tool-registration test using a fake FastMCP. |

## Data flow

CSV files in `data/kaggle/` → `_read_rows` (utf-8-sig) → per-source
`_matches_from_rows` normalizes heterogeneous schemas (Portuguese/English
columns, multiple date formats) into `Match` → queries filter/aggregate over the
in-memory tuple. A `_canonical_statistical_matches` step de-duplicates the same
fixtures appearing across overlapping source files so statistics aren't
double-counted. FIFA players load into dicts with a rich attribute sub-map.

## Notable design points

- Cross-file query (`team_overview`) joins match CSVs with the FIFA player CSV.
- Standings and all records are **computed** from match results, not hardcoded.
- `answer_question` provides a bounded English/Portuguese intent router (not
  open-ended NLU) over the structured queries — an enhancement beyond spec.
- Service is deliberately MCP-independent (MCP imported lazily) so the query
  layer is testable without the MCP runtime.
