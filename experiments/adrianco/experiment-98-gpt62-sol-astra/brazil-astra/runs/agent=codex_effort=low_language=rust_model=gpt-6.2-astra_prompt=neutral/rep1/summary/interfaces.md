# Interfaces

## MCP tools (JSON-RPC 2.0 over stdio)

| Method | Params | Returns | Handler |
|--------|--------|---------|---------|
| initialize | protocolVersion | capabilities + serverInfo | `main.rs:rpc` |
| ping | — | `{}` | `main.rs:rpc` |
| tools/list | — | one tool: `query_soccer` | `main.rs:rpc` |
| tools/call | name, arguments.sql | `{content:[{type:text,text}], isError}` | `main.rs:rpc` → `query()` |

The sole tool is `query_soccer(sql: string)` — it runs one read-only `SELECT` against the
in-memory database. All query categories (match/team/player/competition/stats) are expressed
as SQL rather than as separate tools. Results are capped at 100 rows with a `truncated` flag and a
4-second statement deadline.

## Data schema (in-memory SQLite)

- `matches(id, competition, date, season, round, stage, home, away, home_goal, away_goal, derby)` — reconciled fixtures (one row per real match, deduplicated across source CSVs).
- `records(id, source, competition, date, season, round, stage, home, away, home_goal, away_goal, fixture, attributes)` — every raw CSV match row, linked to `matches.id`; `attributes` is JSON of original columns.
- `players(id, name, age, nationality, overall, potential, club, club_key, position, attributes)` — FIFA snapshot; `attributes` is JSON of all original player columns.
- `team_results` (view) — two perspectives per fixture with `win/draw/loss/points`.
- `standings` (view) — per competition+season aggregates with window-function `rank`.
- SQL functions: `team_key(name)` (canonical team folding), `fold(name)` (accent/caseinsensitive).

## CLI

`soccer-mcp [data_dir]` — optional positional arg for the Kaggle CSV directory (defaults to
`$CARGO_MANIFEST_DIR/data/kaggle`). Otherwise reads JSON-RPC requests line-by-line from stdin.
