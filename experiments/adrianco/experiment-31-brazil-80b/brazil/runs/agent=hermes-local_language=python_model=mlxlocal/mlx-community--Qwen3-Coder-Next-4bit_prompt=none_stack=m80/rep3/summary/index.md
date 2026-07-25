# Run Summary — Brazilian Soccer "MCP" Server (Python)

## Surface

The task asks for an **MCP (Model Context Protocol) server** exposing tools to query
Brazilian soccer data (matches, teams, players, competitions, statistics) loaded from
the six CSVs in `data/kaggle/`. See `modules.md` and `interfaces.md`.

## Architecture at a glance

- **Single-module design** (`server.py`, 815 LOC). Loads all six CSVs at import time into
  a module-global `DATA` dict of pandas DataFrames.
- **Interface is FastAPI REST, not MCP.** The project is named "MCP Server" in docstrings
  and the root payload, but there is **no MCP SDK, no stdio transport, and no
  tool/resource registration** — it exposes five HTTP `POST` endpoints instead. "MCP"
  appears only as free text (server.py:3, :360, :412).
- **Query layer**: pure functions (`normalize_team_name`, `get_team_matches`,
  `get_head_to_head`, `calculate_team_stats`, `calculate_standings`,
  `calculate_top_scorers`, `format_match`) sit under thin endpoint wrappers. These
  functions — not the HTTP layer — are what the test suite exercises.
- **Data model**: all match DataFrames are `pd.concat`-ed on the fly per request, which
  loses the per-file competition identity (see interfaces.md and findings).

## Control flow

Import → `load_data()` reads 6 CSVs → module globals `DATA`, FastAPI `app`.
Request → endpoint concatenates relevant DataFrames → applies filters → maps rows through
`format_match` → returns JSON.

## Modules / interfaces

See `modules.md` and `interfaces.md` in this directory.
