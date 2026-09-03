# Architecture Summary

Single-file Go HTTP service (`main.go`, 235 LOC) plus one test file (`main_test.go`, 21 LOC).

## Modules / flow

- **`main`** — one package, one file.
  - `initDB()` — opens `./books.db` via `github.com/mattn/go-sqlite3`, creates the `books` table (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn`).
  - Router: `github.com/gorilla/mux`, registered in `main()`:
    - `GET /health` → `healthHandler`
    - `POST /books` → `createBookHandler`
    - `GET /books` → `getBooksHandler` (supports `?author=` via `LIKE %..%`)
    - `GET /books/{id}` → `getBookHandler`
    - `PUT /books/{id}` → `updateBookHandler`
    - `DELETE /books/{id}` → `deleteBookHandler`
  - Global `var db *sql.DB` shared by all handlers.

## Interfaces

- `Book` struct with JSON tags (`id`, `title`, `author`, `year`, `isbn`).
- All handlers write `application/json`; status codes: 201 (create), 200 (default), 400 (bad JSON / missing title|author / bad id), 404 (not found), 500 (DB errors).

## Testability note

Handlers reference the package-global `db`, which is only initialized by `initDB()` (opens a real file DB). The single test covers `healthHandler` (no DB needed); the five CRUD handlers are not exercised by any test, which is why measured coverage is ~1.6%.

*(Generated inline; the standalone `run-summary` skill was not separately invoked.)*
