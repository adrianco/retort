# Architecture Summary

> The `run-summary` skill is not registered for direct invocation in this session; this is a lightweight hand-written summary in its place.

## Overview

Single-file **Flask + SQLite** REST API for a book collection.

## Modules

| File | Role |
|------|------|
| `app.py` | Entire application: DB helpers, schema init, validation, and all 6 routes. |
| `tests/test_api.py` | 19 pytest integration tests — **but they reimplement the app inline** (`create_test_app`) rather than importing `app.py`. |
| `README.md` | Setup, run, and endpoint documentation with curl examples. |

## Interfaces (routes in `app.py`)

- `GET  /health` — DB ping, `{status: healthy}` (app.py:74)
- `GET  /books` — list, optional `?author=` filter (app.py:85)
- `POST /books` — create, 201 (app.py:110)
- `GET  /books/<int:id>` — fetch one, 404 if absent (app.py:140)
- `PUT  /books/<int:id>` — full-replace update, 404 if absent (app.py:160)
- `DELETE /books/<int:id>` — delete, 404 if absent (app.py:195)

## Data flow

Per-request SQLite connection cached on Flask `g`, closed in `teardown_appcontext`.
Schema (`books`: id, title, author, year, isbn, created_at, updated_at) created by
`init_db()` at startup. Validation (`validate_book`) enforces required `title`/`author`
and an optional integer `year` in 0–9999.

## Key observation

Tests exercise a **duplicate** of the application defined inside the test file, so
`app.py` itself has no direct test coverage. The two implementations can drift without
any test failing.
