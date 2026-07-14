# Architecture Summary

Single-package Go service (`package main`) implementing a book-collection REST API.

## Modules / files

| File | Role |
|------|------|
| `app.go` (280 LOC) | Entire application: model types, DB init, six HTTP handlers, router wiring in `main`. |
| `app_test.go` (353 LOC) | 11 integration tests exercising every route via `httptest`. |
| `go.mod` / `go.sum` | Gin (`gin-gonic/gin`) + SQLite driver (`mattn/go-sqlite3`). |
| `README.md` | Setup, run, and per-endpoint curl usage. |

## Interfaces (HTTP)

- `GET /health` → `healthHandler`
- `POST /books` → `createBookHandler` (binds `CreateBookRequest`, `binding:"required"` on title/author + explicit empty-string check)
- `GET /books` (`?author=`) → `listBooksHandler`
- `GET /books/:id` → `getBookHandler`
- `PUT /books/:id` → `updateBookHandler` (fetch-then-merge; empty/zero fields fall back to existing values)
- `DELETE /books/:id` → `deleteBookHandler`

## Data flow

Handlers talk directly to a package-global `*sql.DB` (`database/sql` + go-sqlite3). Production `main` opens a file-backed DB (`./books.db`, created via `CREATE TABLE IF NOT EXISTS`); tests swap in an in-memory `:memory:` DB and rebuild a fresh router in `setupRouter`. No repository/service layer — handlers embed SQL inline. Responses are JSON via `gin.H` / struct marshaling with explicit status codes (201/200/400/404/500).

## Notes

- No pagination or auth (not required by the spec).
- `updateBookHandler` uses zero-value sentinels to detect "field omitted", so a client cannot deliberately set `year=0` or clear a string field — a minor PATCH-vs-PUT semantic quirk, not a spec violation.
