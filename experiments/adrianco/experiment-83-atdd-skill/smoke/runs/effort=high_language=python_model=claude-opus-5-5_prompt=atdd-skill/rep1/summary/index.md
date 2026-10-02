# Architecture Summary — brazilian-soccer-mcp

> Produced inline by `evaluate-run` (the `run-summary` skill is not exposed as an
> invocable skill in this session). Structure captured from a static read.

## Package `brazilian_soccer_mcp/` (1,791 LOC, stdlib-only, zero runtime deps)

| Module | LOC | Role |
|--------|-----|------|
| `server.py` | 305 | MCP server. Hand-rolled JSON-RPC 2.0 over stdio (`initialize`/`ping`/`tools/list`/`tools/call`), 16 tool definitions with input schemas, arg validation, `QueryError` → tool-error mapping. No MCP SDK dependency. |
| `queries.py` | 691 | Query engine. `SoccerQueries` exposes find_matches, head_to_head, team_record, team_competitions, team_profile, standings, cup_finals, knockout_bracket, find_derbies, competition_stats, biggest_wins, rank_teams, compare_seasons, search_players, player_profile, brazilian_club_players, dataset_info. |
| `data.py` | 327 | Loads all 6 Kaggle CSVs into `Match`/`Player` dataclasses; multi-format date parsing; de-dupes matches across overlapping files; merges extended stats. |
| `teams.py` | 206 | Team-name identity: normalizes accents/state suffixes/full club names to a stable key (`TeamRegistry`, `fold`, `identify`). |
| `formatting.py` | 258 | Renders each query result to human-readable text (the MCP `text` content block). |
| `__main__.py` | 3 | `python -m brazilian_soccer_mcp` entrypoint → `server.main`. |

## Flow

`__main__` → `server.main()` loads `SoccerData` once at start-up (from `$SOCCER_DATA_DIR`
or `data/kaggle`), wraps it in `SoccerQueries`, then serves JSON-RPC over stdio. Each
`tools/call` dispatches to a `SoccerQueries` method and returns both readable text and
`structuredContent`.

## Tests (1,561 LOC) — four-layer ATDD structure

- `tests/acceptance/` — executable specs in problem-domain language (`*Spec` classes,
  `should_*` methods): match_search, team_records, player_search, competitions,
  statistics, provided_datasets.
- `tests/acceptance/dsl/` — the DSL layer (matches, teams, players, competitions,
  statistics, dataset, provided_data) expressing intent, not mechanics.
- `tests/acceptance/drivers/` — the protocol driver: `mcp_driver.py` + `mcp_client.py`
  drive the system through its real public MCP interface (spawns the server, speaks
  JSON-RPC); `kaggle_files.py` seeds synthetic datasets.
- `tests/unit/` — focused unit tests for data, teams, server.

This is textbook Dave-Farley ATDD layering (spec → DSL → protocol driver → system),
which is exactly what the `atdd-skill` prompt factor asked for.
