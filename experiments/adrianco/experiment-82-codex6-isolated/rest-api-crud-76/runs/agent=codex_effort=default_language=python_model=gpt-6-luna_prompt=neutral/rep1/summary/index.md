# Architecture summary

Single-module WSGI service, Python standard library only (no third-party framework).

## Modules

- **`app.py`** (131 LOC) — the whole service.
  - `BookStore` — owns the SQLite connection factory and creates the `books` table
    (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn`). DB path from
    the `BOOKS_DB` env var, default `books.db`.
  - `BooksAPI` — the WSGI callable. Helpers: `response` (JSON + status + Content-Length),
    `read_json` (body parse with error handling), `validate` (title/author required,
    type-checks year/isbn), `book` (row → dict). `__call__` routes on
    `(method, path)` via a `re.fullmatch(r"/books(?:/(\d+))?/?")` match.
  - `app = BooksAPI()` module-level instance; `__main__` serves it with
    `wsgiref.simple_server` on `$PORT` (default 8000).
- **`test_app.py`** (63 LOC) — `unittest` suite driving the WSGI callable in-process
  against a temp SQLite file (no socket).

## Request flow

`__call__` → `/health` short-circuit → regex route match → per-(method, id) branch →
SQLite query via a fresh `store.connect()` context → `response(...)`. `ValueError`
from `read_json`/`validate` is caught and returned as `400`.

## Endpoints

`GET /health`, `POST /books`, `GET /books` (`?author=` exact filter),
`GET /books/{id}`, `PUT /books/{id}` (full replace), `DELETE /books/{id}`.
Unknown paths → 404; parameterised SQL throughout (no injection surface).
