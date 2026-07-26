# Architecture Summary

Two-file Flask application (`run-summary` skill not available as a Skill-tool
entry; this is a hand-written summary of a trivially small codebase).

## Modules

- **`app.py`** (161 LOC) — the whole service.
  - `get_db()` — module-level connection helper keyed on Flask `g`. **Unused**
    by the app factory (dead code; `create_app` defines its own `_conn`).
  - `init_db(db_path)` — creates the `books` table (id PK, title/author NOT NULL,
    year, isbn) if absent. Called once inside `create_app`.
  - `row_to_book(row)` — sqlite3.Row → dict serializer.
  - `create_app(db_path=None)` — application factory. Registers routes, a
    per-request `_conn()` connection (cached on `g`), and a `teardown_appcontext`
    that closes the connection. Enables testability via injected `db_path`.
- **`test_app.py`** (99 LOC) — 7 pytest tests using a `tempfile` SQLite DB per
  test via the `client` fixture.

## Routes / interfaces

| Route | Method | Behavior |
|-------|--------|----------|
| `/health` | GET | `{"status":"ok"}`, 200 |
| `/books` | POST | validate title+author (and int year) → insert → 201 with body |
| `/books` | GET | list all, or `?author=` exact-match filter, 200 |
| `/books/<int:id>` | GET | one book or 404 |
| `/books/<int:id>` | PUT | partial update (defaults to existing fields) or 404 |
| `/books/<int:id>` | DELETE | delete or 404, 204 on success |

## Flow

Request → `_conn()` (lazy sqlite3 connect, cached on `g`) → parametrized SQL →
`row_to_book` → `jsonify`. Connection closed on app-context teardown. Storage is
persistent SQLite on disk (`BOOKS_DB` env var, default `books.db`).
