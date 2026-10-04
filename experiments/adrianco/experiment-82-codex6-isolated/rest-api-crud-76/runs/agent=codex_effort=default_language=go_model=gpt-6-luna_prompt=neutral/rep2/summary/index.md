# Codebase Summary

Single-package Go service (`package main`, module `bookapi`) implementing a book-collection REST API over the standard library `net/http` and a pure-Go SQLite driver (`modernc.org/sqlite`).

## Modules / files

| File | Role |
|------|------|
| `main.go` (258 LOC) | Entire service: model, router, handlers, helpers, `main()` |
| `main_test.go` (99 LOC) | 3 integration tests over an in-memory SQLite DB |
| `README.md` | Setup, run, endpoint, and test instructions |

## Structure of `main.go`

- **`Book`** — struct with `id`/`title`/`author`/`year`/`isbn` JSON tags.
- **`API`** — wraps `*sql.DB`. `NewAPI` creates the `books` table (idempotent `CREATE TABLE IF NOT EXISTS`) with `NOT NULL` constraints.
- **`API.ServeHTTP`** — hand-rolled router. Dispatches by exact path (`/health`, `/books`) and prefix (`/books/`), branching on HTTP method; returns `405` with an `Allow` header for unsupported methods and `404` for unknown paths.
- **Handlers** — `createBook`, `listBooks` (with optional `?author=` exact-match filter), `getBook`, `updateBook`, `deleteBook`. Each uses parameterized SQL via `*Context` methods and maps DB state to status codes (`201`/`200`/`204`/`404`/`400`/`500`).
- **Helpers** — `decodeBook` (strict JSON: `DisallowUnknownFields`, `MaxBytesReader`, single-object enforcement, trims + validates title/author, rejects negative year), `scanBook`, `writeJSON`, `writeError`, `methodNotAllowed`.
- **`main()`** — opens SQLite (`BOOKS_DB` env, default `books.db`), sets `MaxOpenConns(1)`, listens on `ADDR` (default `:8080`).

## Flow

Request → `ServeHTTP` route match → method switch → handler → parameterized SQL → `writeJSON`/`writeError`. Persistence is real SQLite; tests inject an in-memory DB through the same `NewAPI` seam.
