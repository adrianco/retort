# Architecture Summary

Single-package Go HTTP service (`package main`) implementing a Book CRUD REST API.

## Modules / Files

| File | Role |
|------|------|
| `app.go` | Entire application: data models, DB init, 6 HTTP handlers, `main()` wiring. |
| `app_test.go` | 12 integration tests exercising every route via `httptest` + in-memory SQLite. |
| `README.md` | Setup, run, and curl usage docs. |
| `go.mod` / `go.sum` | Gin (`gin-gonic/gin`) + SQLite (`mattn/go-sqlite3`) dependencies. |

## Interfaces (routes)

`main()` (app.go:314) builds a `gin.Default()` engine and registers:

- `GET /health` → `healthHandler` (app.go:100)
- `POST /books` → `createBookHandler` (app.go:105)
- `GET /books` → `listBooksHandler` (app.go:150, `?author=` filter)
- `GET /books/:id` → `getBookHandler` (app.go:186)
- `PUT /books/:id` → `updateBookHandler` (app.go:211)
- `DELETE /books/:id` → `deleteBookHandler` (app.go:286)

## Data / persistence

- SQLite via `database/sql` + `mattn/go-sqlite3`.
- Production: `initDB()` (app.go:43) opens a file DB `./books.db`.
- Tests: `openDB()` (app.go:75) opens `:memory:`; `setupTest` assigns it to the package-global `db`.
- Schema: single `books` table (id AUTOINCREMENT, title, author, year, isbn — all NOT NULL).

## Flow

Request → Gin router → handler → parameterized `database/sql` query → `c.JSON(status, …)`.
State is held entirely in SQLite; the only shared mutable state is the package-global `*sql.DB`.

## Notes

- Handlers reference a **package-global `db`** rather than taking it via injection; tests
  swap the global, so tests are not parallel-safe (acceptable for this scale).
- `updateBookHandler` uses pointer fields (`*string`/`*int`) to support **partial** updates —
  an enhancement beyond the spec's plain "update a book".
