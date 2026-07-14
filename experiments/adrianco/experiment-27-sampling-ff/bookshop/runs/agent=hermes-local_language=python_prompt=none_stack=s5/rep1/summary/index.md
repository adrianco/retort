# Architecture Summary

_Inline summary (run-summary skill not delegated; app is small enough to summarize directly)._

## Modules

| File | Role | LOC |
|------|------|-----|
| `app.py` | Flask application: 6 book routes + `/health`, SQLite persistence, validation | 187 |
| `test_app.py` | pytest suite, 17 tests across 6 test classes, temp-DB fixture | 236 |
| `requirements.txt` | `flask>=3.0`, `pytest>=7.4` | 2 |
| `README.md` | Setup, run, and API docs with curl examples | — |

## Design

- **Web layer:** Flask with route decorators. Single module, no blueprints (appropriate for scope).
- **Persistence:** SQLite via stdlib `sqlite3`. Per-request connection stored on Flask `g` with `teardown_appcontext` cleanup (`app.py:10-23`). Schema created idempotently in `init_db()` (`app.py:26-39`), invoked at import time (`app.py:183`).
- **Serialization:** `book_to_dict()` maps `sqlite3.Row` → JSON dict (`app.py:42-50`).
- **Validation:** title/author required + trimmed; optional `year` coerced to int with 400 on failure (`app.py:70-83`, `142-155`).

## Request flow

`request → get_json → validate → get_db() (g-cached conn) → SQL execute/commit → book_to_dict → jsonify(status)`

## Endpoints

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health_check` | 200 |
| POST | `/books` | `create_book` | 201/400 |
| GET | `/books` (`?author=`) | `list_books` | 200 |
| GET | `/books/<id>` | `get_book` | 200/404 |
| PUT | `/books/<id>` | `update_book` | 200/400/404 |
| DELETE | `/books/<id>` | `delete_book` | 200/404 |

## Test approach

Class-per-endpoint; temp SQLite file per test via `tempfile.mkstemp` + `init_db()` re-init (`test_app.py:12-27`). Covers happy paths, 400 validation, 404 not-found, author filtering, and partial-update field preservation.
