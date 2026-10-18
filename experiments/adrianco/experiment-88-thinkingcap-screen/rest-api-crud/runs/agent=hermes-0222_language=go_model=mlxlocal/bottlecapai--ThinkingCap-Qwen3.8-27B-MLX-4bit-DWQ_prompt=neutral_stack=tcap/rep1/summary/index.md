# Architecture Summary — book-api (Go)

A single-package (`package main`) Go REST service for a book collection, 355 source
LOC across 3 files plus a 302-LOC test file. No web framework: it uses the Go 1.22+
`net/http` method/wildcard router and the pure-Go `modernc.org/sqlite` driver (no CGO).

## Modules

| File | Role |
|------|------|
| `main.go` | Entry point. Opens the SQLite DB (`BOOKS_DB` env, default `books.db`), runs `initDB`, reads `PORT` (default 8000), starts `http.ListenAndServe` with `NewHandler`. |
| `server.go` | HTTP layer: `Book`/`bookInput`/`errorResponse` types, `NewHandler` route table, the seven handlers (health, root, CRUD), request decode + `validateBookInput`, `parseID`, and `writeJSON`/`writeError` helpers. |
| `store.go` | Persistence: `initDB` (CREATE TABLE books), `getBook`, and the `scanBookRow`/`scanBook`/`applyNullable` row-scanning helpers that map NULL year/isbn to Go. |
| `server_test.go` | 9 integration/unit tests, each against a throwaway temp-dir DB via `httptest.Server`. |

## Interfaces (routes)

`GET /health`, `GET /` (service info), `POST /books`, `GET /books` (`?author=` filter),
`GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}`.

## Flow

`main` → `NewHandler(db)` builds a `*http.ServeMux` bound to a `handler{db}`. Each request
decodes/validates input, executes a parameterised SQL statement, reloads the affected row
via `getBook`, and emits JSON with the right status (201 create, 200 read/update, 204
delete, 400 validation, 404 missing, 500 DB error). Persistence is real SQLite on disk;
tests isolate state with `t.TempDir()`.

## Observations

- Clean separation (handlers / persistence / entry point), parameterised SQL throughout
  (no injection), consistent JSON error envelope, `Location` header on create.
- PUT is full-replacement semantics (omitted fields cleared) — documented in README and
  asserted by `TestUpdateBook`.
- Validation goes beyond the spec (year range 1–9999, ISBN length ≤32) — enhancement, not
  a deduction.
