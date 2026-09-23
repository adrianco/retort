# Architecture Summary

Single-module Flask + SQLite REST service.

## Modules

| File | Role |
|------|------|
| `app.py` | Entire service: app factory, DB wiring, validation, and all routes (114 lines) |
| `tests/test_app.py` | pytest suite (6 functions, one parametrized ×5) against a `tmp_path` SQLite DB |

## Structure of `app.py`

- **`create_app(db_path=None)`** — application factory. Resolves the DB path from
  the argument, then `BOOKS_DB` env, then `books.db`. Creates the `books` table
  (`id`, `title NOT NULL`, `author NOT NULL`, `year`, `isbn`) at startup.
- **`get_db()` / `close_db()`** — per-request SQLite connection stored on Flask `g`,
  `row_factory=sqlite3.Row`, closed on app-context teardown.
- **`validate(data)`** — enforces `title`/`author` as non-empty strings, `year` as an
  `int` (rejecting `bool`), `isbn` as a string; returns `(cleaned, error)`.
- **`fetch(book_id)`** — single-row lookup helper returning a dict or `None`.

## Routes

| Method | Path | Behaviour |
|--------|------|-----------|
| GET | `/health` | `{"status":"ok"}` |
| POST | `/books` | validate → INSERT → 201 with created row; 400 on validation error |
| GET | `/books` | list all, or exact `?author=` filter, ordered by `id` |
| GET | `/books/<int:id>` | one book or 404 |
| PUT | `/books/<int:id>` | 404 if absent, else validate → full-row UPDATE → 200 |
| DELETE | `/books/<int:id>` | 404 if absent, else DELETE → 204 |

## Flow

Requests hit a route → acquire the request-scoped connection → validate (writes)
→ execute parameterized SQL → return JSON. Parameterized queries throughout
(no string interpolation into SQL).
