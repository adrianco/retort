# Architecture Summary

Brazilian Soccer MCP Server — Python, FastMCP, pandas.

## Modules

| File | Lines | Role |
|------|-------|------|
| `server.py` | 708 | MCP server. Instantiates `FastMCP`, registers 11 `@mcp.tool()` query tools, `mcp.run()` entrypoint. |
| `data_loader.py` | 205 | Loads the 6 Kaggle CSVs from `data/kaggle/` into pandas DataFrames; team-name normalization; combined-match assembly; team filtering. |
| `tests/test_server.py` | 620 | 78 BDD-style pytest functions across 9 feature classes. |

## Interfaces (MCP tools in `server.py`)

- `search_matches` — filter by team, second team (H2H), competition, season, season range, role, limit.
- `get_team_stats` — W/L/D, points, goals for/against, home/away split.
- `head_to_head` — record + recent matches between two teams.
- `search_players` — FIFA data by name, nationality, club, position (with alias map), min overall.
- `get_standings` — league table computed from match results (points/GD/GF sort).
- `get_biggest_wins` — matches by goal difference.
- `get_competition_stats` — avg goals/match, home/away/draw rates.
- `list_teams`, `get_player_details`, `get_team_seasons` — utility tools (beyond spec).

## Data flow

`data_loader` reads CSV → coerces dtypes → adds `competition`, normalized team columns
(`home_team_norm`/`away_team_norm`), parsed `datetime`/`season` → `@lru_cache` per loader.
`load_all_matches` concatenates the four match sources into a unified schema. Server tools
route to a competition-specific loader (or the combined frame) then aggregate in Python.

## Notes

- Loaders are memoized with `functools.lru_cache(maxsize=1)`, so each CSV is parsed once.
- Team-name normalization strips state suffixes (`-SP`) and maps common variants to canonical names.
- No dependency manifest ships with the run; `data/kaggle/` is not archived (see findings).
