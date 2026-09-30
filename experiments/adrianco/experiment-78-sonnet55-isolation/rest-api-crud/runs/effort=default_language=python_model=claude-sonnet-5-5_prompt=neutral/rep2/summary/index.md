# Architecture summary — rest-api-crud (python, claude-sonnet-5-5, rep2)

*The `run-summary` skill is not registered as invocable in this session; this is a
lightweight hand-written summary of the (small) codebase.*

## Modules

| File | Lines | Role |
|------|-------|------|
| `app.py` | 154 | The entire service: DB layer, validation, WSGI app, routing, and a `__main__` server entry point. |
| `test_app.py` | 72 | Pytest suite (7 tests) driving the WSGI app in-process via a `client` fixture. |
| `README.md` | 18 | Setup, run, and endpoint documentation. |

No external runtime dependencies — Python standard library only (`wsgiref`, `sqlite3`,
`json`, `re`, `urllib.parse`). `pytest` is the only (test-time) dependency.

## Interfaces

- **`connect(path)`** — opens SQLite, sets `row_factory`, creates the `books` table
  (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn`).
- **`validate(data) -> (clean, errors)`** — enforces non-empty string `title`/`author`,
  integer-or-null `year` (rejects bool), string-or-null `isbn`.
- **`App`** — WSGI callable. `dispatch()` routes by method + path; handlers
  `create/list/get/update/delete` map to the CRUD verbs; `read_json()` parses the body
  and reports malformed JSON as a 400. `row()` fetches a book as a dict.

## Flow

Request → `App.__call__` (wraps handler, serializes JSON, sets Content-Type/Length,
catches unexpected errors as 500) → `dispatch` → per-route handler → SQLite → JSON body
+ status code. Routes: `/health` (GET), `/books` (POST create, GET list with optional
`?author=`), `/books/{id}` (GET/PUT/DELETE), 404 for anything else, 405 for wrong method
on a known path.

## Notable design choices

- Single-file, stdlib-only implementation (TASK.md named no framework and the venv only
  carried pytest) — zero-install to run.
- Parameterized SQL throughout (no string interpolation) — no SQL-injection surface.
- Persistence is a real on-disk SQLite file (`books.db`, overridable via `BOOKS_DB`),
  satisfying the embedded-DB requirement rather than in-memory dict state.
