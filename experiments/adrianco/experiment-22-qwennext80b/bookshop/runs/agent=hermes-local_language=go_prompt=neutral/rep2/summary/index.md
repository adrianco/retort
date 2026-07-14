# Architecture Summary — book-api (Go)

REST API for a book collection, built with Go stdlib + Gorilla Mux + SQLite (mattn/go-sqlite3), using a clean layered layout.

## Modules

| Package | File | Responsibility |
|---------|------|----------------|
| `main` | `cmd/main.go` | Entry point: opens SQLite DB, runs migration, wires router, registers routes, listens on `$PORT` (default 8080). |
| `handler` | `internal/handler/book_handler.go` | HTTP handlers for all 6 endpoints + health. Decodes JSON, validates title/author, maps store errors to status codes. |
| `model` | `internal/model/book.go` | `Book` struct + `BookStore` — SQLite-backed CRUD (`CreateBook`, `GetBook`, `GetAllBooks`, `GetBooksByAuthor`, `UpdateBook`, `DeleteBook`). |
| `migrate` | `internal/migrate/migrate.go` | `Migrate(db)` — `CREATE TABLE IF NOT EXISTS books`. |
| `handler` (test) | `internal/handler/book_handler_test.go` | 6 test funcs (testify) using `:memory:` SQLite + `httptest`. |

## Request flow

```
HTTP request → mux.Router (main.go) → BookHandler method
  → decode/validate → BookStore method → database/sql → SQLite (books.db)
  → JSON-encode response + status code
```

## Interfaces

- Routes (main.go:32-37): `GET /health`, `GET /books`, `POST /books`, `GET|PUT|DELETE /books/{id}`.
- `BookStore` is a concrete struct (no interface abstraction); handler holds it directly.
- Book JSON model includes server-managed `id`, `created_at`, `updated_at`.

## Notable design choices

- Validation lives in the handler (title/author required) for both Create and Update.
- Store errors surfaced via string comparison (`err.Error() == "book not found"`) rather than sentinel/`errors.Is`.
- `UpdateBook`/`DeleteBook` do not inspect `RowsAffected`, so missing-row 404 handling in the handler is unreachable (see findings.jsonl).
