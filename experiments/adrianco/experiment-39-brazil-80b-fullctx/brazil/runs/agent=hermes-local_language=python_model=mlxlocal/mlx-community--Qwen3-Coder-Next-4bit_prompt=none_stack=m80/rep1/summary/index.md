# Codebase Summary

> Generated inline by `evaluate-run` (the `run-summary` skill is not user-invocable in this session).

## Shape

A two-file, single-class Python project — a **query library**, not a protocol server:

| File | Lines | Role |
|------|------:|------|
| `mcp_server.py` | 692 | `BrazilianSoccerMCP` class: CSV loading + query methods; a `main()` demo |
| `test_mcp_server.py` | 458 | `unittest` BDD suite, 31 tests across 9 `TestCase` classes |

No package layout, no dependency manifest (`requirements.txt`/`pyproject.toml` absent),
stdlib-only (`csv`, `re`, `datetime`, `collections`).

## Modules & flow

- **Data loading** (`_load_*`, `_load_data`) — reads all 6 CSVs from `data/kaggle/` at
  construction into two in-memory lists, `self.matches` (~24k rows) and `self.players`
  (~18k rows). Each match dict is tagged with a `competition` label and pre-normalized
  team names (`home_team_normalized`/`away_team_normalized`).
- **Normalization helpers** — `_normalize_team_name` strips `-SP`/`-RJ` state suffixes and
  parenthetical annotations; `_safe_int` coerces `NA`/blank to a default; `_parse_brazilian_date`
  converts `DD/MM/YYYY`→ISO; `_extract_year` pulls a 4-digit year.
- **Query surface** (public methods) — matches (`get_matches_by_teams`, `_by_competition`,
  `_by_season`, `search_matches`, `get_match_details`), teams (`get_team_stats`,
  `get_head_to_head`, `get_team_competition_history`), players (`get_player_by_name`,
  `get_players_by_club`, `get_brazilian_players`, `get_top_players`), competitions
  (`get_competition_standings`), stats (`get_average_goals`, `get_biggest_victories`).
- **Entrypoint** — `main()` instantiates the class and prints a few canned example queries;
  it does **not** start any server or speak a protocol.

## Architecture note

The class is named `…MCP` and the file `mcp_server.py`, but there is **no Model Context
Protocol layer**: no `mcp`/`fastmcp` SDK import, no tool/resource registration, no
stdio/JSON-RPC transport. The query methods are the building blocks an MCP tool layer would
wrap, but that layer is absent. See finding `R1` in `findings.jsonl`.
