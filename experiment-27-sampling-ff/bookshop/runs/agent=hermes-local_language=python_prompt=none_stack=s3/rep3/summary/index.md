# Architecture Summary

> Generated inline by `evaluate-run` (the `run-summary` skill was not registered as invocable in this session). Codebase is small (2 source files, 383 LOC), so the summary is authored directly.

## Overview

A minimal Flask + SQLite REST API for a book collection. Single-module design — all
routes and persistence live in `app.py`; tests live in `test_app.py`.

## Modules

| File | Role |
|------|------|
| `app.py` | Flask app: DB connection management, schema init, and all six CRUD/health routes. |
| `test_app.py` | pytest suite (16 tests) using Flask's `test_client` against a temp SQLite DB. |
| `requirements.txt` | `flask>=3.0.0`, `pytest>=7.0.0`. |
| `README.md` | Setup, run, and curl usage examples. |

## Persistence

- SQLite file `books.db` next to `app.py` (`DATABASE` path, `app.py:7`).
- `get_db()` (`app.py:10`) caches a per-request connection on Flask `g`; `close_db()`
  (`app.py:18`) tears it down via `teardown_appcontext`. `row_factory = sqlite3.Row`
  yields dict-able rows.
- `init_db()` (`app.py:26`) creates the `books` table (`id` PK autoincrement, `title`
  NOT NULL, `author` NOT NULL, `year`, `isbn`) and runs at import time (`app.py:174`).

## Routes

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health_check` `app.py:44` | 200 |
| POST | `/books` | `create_book` `app.py:50` | 201 / 400 |
| GET | `/books` | `list_books` `app.py:93` | 200 (optional `?author=` LIKE filter) |
| GET | `/books/<id>` | `get_book` `app.py:110` | 200 / 404 |
| PUT | `/books/<id>` | `update_book` `app.py:122` | 200 / 400 / 404 |
| DELETE | `/books/<id>` | `delete_book` `app.py:158` | 200 / 404 |

## Request flow

Client → Flask route → `get_db()` (parameterized SQL, no string interpolation) →
`jsonify(...)` + status code. Validation for `title`/`author` happens inline in
`create_book` and `update_book` before any write.

## Notes

- All SQL is parameterized (`?` placeholders) — no injection surface.
- `?author=` is a substring `LIKE %...%` match, not exact.
- `update_book` requires both `title` and `author` on every PUT (full-replace
  semantics, not partial patch).
