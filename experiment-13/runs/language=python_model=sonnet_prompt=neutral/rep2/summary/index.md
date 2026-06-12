# Architecture Summary

Brazilian Soccer MCP server. Two modules + a test suite.

## Modules

### `data_loader.py` (219 LOC)
Loads and unifies six Kaggle CSVs from `data/kaggle/` into a single pandas
match DataFrame plus a FIFA player DataFrame.

- **Team normalization** — `normalize_team()` strips state suffixes (`-SP`),
  parenthetical notes, lowercases, and maps a hand-written alias table
  (e.g. `sao paulo` → `são paulo`, `atletico-mg` → `atlético mineiro`).
- **Per-source loaders** — `load_brasileirao`, `load_copa_brasil`,
  `load_libertadores`, `load_br_football`, `load_historico`, `load_fifa`.
  Each parses mixed-format dates (`_parse_dates`), coerces goals to numeric,
  and tags a `competition` label.
- **Unification** — `load_all_matches()` concatenates the five match sources
  on common columns, dedups on (datetime, teams, goals), sorts by date.
- **Caching** — module-level `_matches` / `_fifa` memoized via `get_matches()`
  / `get_fifa()`.

### `server.py` (532 LOC)
`FastMCP("Brazilian Soccer Knowledge Graph")` exposing 8 `@mcp.tool()` handlers:

| Tool | Capability |
|------|-----------|
| `search_matches` | filter by team, opponent (h2h), competition, season, date range |
| `get_team_stats` | W/L/D + goals for/against, home/away/competition/season filters |
| `get_competition_standings` | points table computed from match results |
| `search_players` | FIFA search by name / nationality / club / position / min rating |
| `get_biggest_wins` | largest winning margins |
| `get_overall_stats` | avg goals, home/draw/away split |
| `get_top_teams` | rank teams by wins / goals / win_rate / away_wins |
| `list_competitions` | competitions and season ranges available |

Entry point: `mcp.run()` over stdio.

### `test_server.py` (450 LOC)
60 pytest tests across 11 classes covering data loading, normalization, and
each tool. No skips/xfail.

## Data flow
CSV files → per-source loaders (normalize) → `load_all_matches` (concat+dedup)
→ cached DataFrame → tool handlers filter/aggregate → formatted string back to
the MCP client.
