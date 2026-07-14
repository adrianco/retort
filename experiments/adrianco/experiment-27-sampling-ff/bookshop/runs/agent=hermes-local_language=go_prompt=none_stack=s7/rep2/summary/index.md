# Architecture Summary — book-api (Go / Gin / SQLite)

Single-package (`package main`) service in one source file, `app.go` (396 LOC).

## Modules / layers

- **Data model** — `Book`, `CreateBookRequest` (`binding:"required"` on title/author),
  `UpdateBookRequest` (`app.go:16-38`).
- **Persistence** — `Database` wraps `*sql.DB` over go-sqlite3 with WAL mode
  (`app.go:41-67`). CRUD methods: `CreateBook`, `GetAllBooks(authorFilter)` (LIKE
  substring, case-insensitive), `GetBook`, `UpdateBook`, `DeleteBook`
  (`app.go:89-211`). Schema created idempotently in `CreateTable` (`app.go:70-81`).
- **HTTP layer** — `main()` builds a `gin.Default()` router and registers all six
  routes inline (`app.go:213-396`): `GET /health`, `POST /books`, `GET /books`,
  `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id`.

## Request flow

Client → gin router → inline handler closure → `Database` method → SQLite. Handlers
own JSON binding, input validation (trim + non-empty title/author), status codes
(201/200/400/404/500), and error wrapping.

## Notable structure

- Handler logic is **duplicated** into the test file's `newTestRouter()`
  (`app_test.go:60-233`) rather than extracted into shared, testable functions.
  Consequence: `main()`'s handlers are never executed by the suite (coverage 26.3%).
- PUT uses zero-value sentinels (empty string / `year==0`) to mean "keep existing"
  (`app.go:341-356`) — partial-update semantics, not strict replace.
