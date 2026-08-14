# Architecture summary

`run-summary` skill not available in this session; concise hand-written map below.

## Modules (`brazilian_soccer_mcp/`)

| Module | Lines | Role |
|--------|------|------|
| `server.py` | 348 | FastMCP transport adapter; registers 18 tools + `soccer://datasets` resource; falls back to `FallbackMCP` if the SDK import is unhealthy. CLI `main()` with stdio/sse/http transports. |
| `service.py` | 1546 | `SoccerQueryService` — all query logic: match search, team/competition stats, standings, head-to-head, player search, NL router (`answer_question`), plus dedup (`_deduplicate`) and single-source-per-season (`_coherent_records`) safeguards. |
| `repository.py` | 426 | `SoccerCatalog` — loads all 6 CSVs per `DATASET_SPECS`, validates required columns, builds team/season/competition/name/club/nationality indexes. |
| `normalization.py` | 220 | Team/competition/text normalization (state-suffix stripping, accents), multi-format date parsing, safe int/float parsing. |
| `models.py` | 113 | `MatchRecord` / `PlayerRecord` dataclasses with derived keys and `is_complete`/`goal_margin` helpers. |
| `fallback_mcp.py` | 273 | Minimal MCP protocol implementation used only when the official SDK is unavailable. |

## Data flow

CSV files → `SoccerCatalog.from_directory` (normalize + index) → `SoccerQueryService` methods → MCP tool handlers → formatted text + structured payload. Aggregates deduplicate overlapping source files before counting.

## Tests (`tests/`, 28 tests)

`test_repository`, `test_normalization`, `test_service` (unit, synthetic catalogs via `conftest.make_catalog`), `test_server` (wiring via `FakeMCP`), `test_integration` (loads real bundled data). One conditional skip guards the subprocess-transport test when the real SDK is present.
