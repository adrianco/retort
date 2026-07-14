# Architecture Summary — Brazilian Soccer MCP Server (python · sonnet · ATDD · rep3)

> Generated inline by `evaluate-run` (the `run-summary` skill was not invoked as a
> sub-agent; this summary follows its module/interface/flow structure).

## Modules

| File | Role | LOC |
|------|------|-----|
| `server.py` | MCP entrypoint. Builds a `FastMCP` instance and registers 6 query tools. | 550 |
| `data_loader.py` | `DataLoader` class + helpers. Reads the 6 Kaggle CSVs, normalises them into one schema. | 194 |
| `tests/test_acceptance.py` | 14 black-box acceptance tests driving the server through the in-memory MCP client/server session. | 421 |
| `tests/test_unit.py` | 32 unit tests over `DataLoader` internals and normalisation helpers. | 182 |

## Interfaces (MCP tools)

All tools are `@mcp.tool()` functions returning JSON strings (`ensure_ascii=False`).

| Tool | Purpose | Key params |
|------|---------|-----------|
| `find_matches` | Search matches; single team, head-to-head pair, competition, season, date range. | `team`, `team1`/`team2`, `competition`, `season`, `date_from`/`date_to`, `limit` |
| `get_team_stats` | Aggregate W/D/L, goals for/against, points, win rate. | `team`, `competition`, `season` |
| `find_players` | Search FIFA player data. | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `get_head_to_head` | Head-to-head record between two teams + recent matches. | `team1`, `team2`, `competition`, `season` |
| `get_standings` | Standings table computed from match results. | `season`, `competition` |
| `get_statistics` | Aggregate stats: `biggest_wins`, `goals_per_match`, `home_win_rate`, `top_scoring_teams`. | `stat_type`, `competition`, `season`, `limit` |

## Data flow

1. **Import time** (`server.py:19-20`): a module-level `DataLoader(DATA_DIR)` is created and `load_all()` eagerly loads all 6 CSVs into pandas DataFrames.
2. **Normalisation** (`data_loader.py`): each loader maps its source columns onto a common schema —
   `date, home_team, away_team, home_goals, away_goals, competition, season, round_or_stage`.
   Team names are normalised via `normalize_team_name` (strips ` -UF` state suffix); dates via `_to_iso_date`
   (handles ISO, Brazilian `DD/MM/YYYY`, and datetime forms); goals via `_parse_goals`.
3. **Query** (`server.py` tools): each tool pulls the relevant frame (`get_all_matches`, per-competition getters,
   or `get_players`), filters with pandas masks, aggregates in Python loops, and returns JSON.

### Notable design choices
- **Duplicate-tolerant union**: `get_all_matches()` concatenates 5 match frames *without* de-duplication
  (`data_loader.py:68-78`). BR-Football "Serie A"/"Copa do Brasil" rows overlap the dedicated Brasileirão/Copa
  CSVs, so unioned queries can double-count. `get_team_stats`/`get_standings` route around this by selecting the
  primary per-competition frame; `get_head_to_head` and `get_statistics` do not.
- **Historical split**: `novo_campeonato_brasileiro.csv` is filtered to pre-2012 to avoid overlap with
  `Brasileirao_Matches.csv` (2012-2022).
- **Name disambiguation**: Brasileirão keeps the `-UF` suffix (to distinguish Atlético-MG vs Atlético-GO);
  other datasets normalise it away. Team filters use case-insensitive substring matching.

## Test architecture (ATDD)
- Acceptance tests connect through `mcp.shared.memory.create_connected_server_and_client_session` and call tools
  via `session.call_tool(...)` — genuine public-interface (MCP protocol) exercise, no internal imports of query
  logic. They assert on domain outcomes (match lists, standings, head-to-head totals).
- Unit tests exercise `DataLoader` and the normalisation helpers directly (finer-grained TDD layer).
