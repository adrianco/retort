# Codebase Summary: Brazilian Soccer MCP Server (python · sonnet · prompt=neutral · rep1)

## Modules

| File | LOC | Role |
|------|-----|------|
| `server.py` | 173 | MCP entrypoint. Builds a `FastMCP("Brazilian Soccer")` instance and registers six `@mcp.tool()` handlers that delegate to `QueryEngine`. `mcp.run()` under `__main__` (stdio transport). |
| `data_loader.py` | 143 | `DataLoader` reads all six Kaggle CSVs from `data/kaggle/`, coerces types, adds normalized name/source columns, and concatenates the five match sources into a unified `all_matches` frame. `normalize_team()` strips state suffixes, parentheticals, and accents. |
| `query_engine.py` | 474 | `QueryEngine` — all query logic over the loaded frames: `search_matches`, `head_to_head`, `get_team_record`, `get_standings`, `search_players`, `get_statistics`. Returns human-formatted strings. |
| `test_server.py` | 340 | 42 pytest tests over `DataLoader`, `normalize_team`, and every `QueryEngine` method, plus two cross-file integration tests. |

## Data flow

```
CSV files (data/kaggle/*.csv)
        │  pandas.read_csv + per-source _load_* + _finalize()
        ▼
DataLoader.all_matches  (unified 5-source match frame, ~24k rows)
DataLoader.fifa         (18k+ players, normalized name/club/nationality cols)
        │
        ▼
QueryEngine  ── 6 query methods, filter via *_norm columns ──▶ formatted str
        │
        ▼
server.py  @mcp.tool() wrappers (empty-string/0 sentinels → None) ──▶ MCP client
```

## Interfaces (MCP tools)

- `search_matches(team, opponent, competition, season, date_from, date_to, limit)`
- `head_to_head(team1, team2, competition, season, limit)`
- `get_team_record(team, competition, season, home_away)`
- `get_standings(season, competition)`
- `search_players(name, nationality, club, position, min_overall, max_overall, limit)`
- `get_statistics(stat_type, competition, season, limit)`

## Design notes

- **Name normalization** is the backbone of matching: a single `normalize_team()` (accent/suffix/parenthetical stripping) feeds `*_norm` columns used for substring filtering, so "Flamengo-RJ" and "Flamengo" unify.
- **Standings de-duplication**: `get_standings` prefers the `brasileirao` source over the overlapping `historico` source for the same season to avoid double-counting.
- **Aggregation grouping** (`get_statistics`, standings table) groups on the *raw* `home_team`/`away_team` columns rather than the normalized ones — a latent robustness gap when a team appears under multiple name spellings within one scope.

*(Generated inline by evaluate-run; the standalone run-summary skill was not invoked.)*
