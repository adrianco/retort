# Architecture Summary

Brazilian Soccer MCP Server — dependency-free Python implementation (stdlib only,
`dependencies = []`). Three source modules + a test module + a PEP 517 build backend.

## Modules

| Module | Lines | Role |
|--------|-------|------|
| `soccer_data.py` | 1662 | Data layer: CSV loading, normalization, `SoccerRepository` query engine |
| `server.py` | 784 | MCP layer: JSON-RPC stdio server, tool schemas, natural-language router |
| `build_backend.py` | ~100 | In-tree PEP 517 backend (avoids external build deps) |
| `tests/test_brazilian_soccer_mcp.py` | 190 | BDD-style acceptance tests (11 tests) |

## Data layer (`soccer_data.py`)

- `SoccerRepository` — loads all 6 bundled CSVs from `data/kaggle/` into `Match` and
  `Player` dataclasses (`ensure_loaded`, `_load_all`, `_make_match`). `dataset_summary`
  reports 23,954 matches + 18,207 players.
- Normalization helpers: `normalize_team_name` (strips state suffixes, accents, aliases
  e.g. "Atlético-GO" → "atletico goianiense"), `normalize_competition_name`,
  `parse_match_date` (handles ISO, `DD/MM/YYYY`, and datetime formats).
- Query methods: `search_matches`, `latest_match`, `team_statistics`, `compare_teams`
  (head-to-head), `standings`, `top_scoring_teams`, `best_team_records`, `biggest_wins`,
  `finals`, `relegated_teams`, `compare_seasons`, `competition_bracket`, `search_players`,
  `top_players`, `team_profile`. Pagination via `_validate_pagination`.
- `_select_authoritative_sources` de-duplicates the overlapping match datasets so
  aggregate stats don't double-count (e.g. 2022 Corinthians home record = 19 games).

## MCP layer (`server.py`)

- `BrazilianSoccerMCPServer._build_tools` registers typed tool definitions
  (`search_matches`, `latest_match`, `team_statistics`, `compare_teams`, `standings`,
  `biggest_wins`, `relegated_teams`, `top_scoring_teams`, `search_players`, …), each with
  JSON-schema `inputSchema`.
- `handle_request` / `run` implement a JSON-RPC 2.0 stdio loop: `initialize`,
  `tools/list`, `tools/call` returning `structuredContent` + `isError`.
- `ask_brazilian_soccer` is a natural-language router mapping questions
  ("Which teams were relegated in 2020?", "Compare the 2018 and 2019 seasons") to tools.

## Flow

`main()` → `get_server()` → `SoccerRepository.from_default_data().ensure_loaded()` →
`server.run(stdin, stdout)` reads JSON-RPC lines, dispatches to `call_tool`, serializes
results with `_mcp_tool_success` / `_mcp_tool_error`.
