# Architecture summary

A single-module Flask + SQLite REST service for a book collection.

## Modules

| File | Role |
|------|------|
| `app.py` | Whole application: schema, DB helpers, validation, and all six routes, wrapped in an app factory `create_app(db_path=None)`. |
| `test_app.py` | Six pytest functions driving Flask's `test_client()` against a per-test SQLite file (`tmp_path`). |
| `requirements.txt` | `flask>=3.0`, `pytest>=8.0`. |
| `README.md` | Setup, run, endpoint, and test docs. |

## Interfaces (routes, all in `app.py`)

- `GET /health` → `{"status": "ok"}` (`app.py:62`)
- `POST /books` → 201 + created row, 400 on invalid body (`app.py:66`)
- `GET /books` → list, optional `?author=` filter (`app.py:79`)
- `GET /books/<int:id>` → row or 404 (`app.py:90`)
- `PUT /books/<int:id>` → full-record update, 404/400 (`app.py:97`)
- `DELETE /books/<int:id>` → 204 or 404 (`app.py:112`)

## Flow

`create_app` builds the Flask app, opens a request-scoped SQLite connection via
`g` (`get_db`, `close_db` teardown), and creates the `books` table once at
startup. `validate()` centralises input checking (title/author required
non-empty strings; year int-if-present; isbn str-if-present). `fetch()`
centralises single-row lookup. JSON `error()` helper and `404`/`405` error
handlers keep responses JSON.

## Design notes

- App-factory pattern lets tests inject an isolated DB path — clean test setup.
- Parameterised SQL throughout (no string interpolation) — no injection surface.
- PUT is a full replace (title+author required on every update), a defensible
  interpretation of "update a book".
