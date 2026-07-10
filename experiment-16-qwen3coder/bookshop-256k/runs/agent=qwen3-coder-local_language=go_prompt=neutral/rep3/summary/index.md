# Architecture Summary

**Book Collection REST API** — Go 1.21 + SQLite (`github.com/mattn/go-sqlite3`). Single-package (`main`) service, ~318 LOC in `main.go`, 183 LOC of tests.

## Modules

| Unit | Location | Responsibility |
|------|----------|----------------|
| `Book` | `main.go:16-22` | Domain model (id, title, author, year, isbn) with JSON tags. |
| `BookStore` | `main.go:24-164` | Persistence layer over `*sql.DB`. CRUD + validation + `HealthCheck` (ping). Table auto-created in `NewBookStore`. |
| HTTP handlers | `main.go:166-318` | `net/http` `DefaultServeMux` routing; per-method dispatch; JSON encode/decode and status-code mapping. |

## Request flow

`http.HandleFunc` registers three route prefixes:
- `/books` → method switch → `handleCreateBook` (POST) / `handleGetBooks` (GET).
- `/books/` → `strconv.Atoi` extracts `{id}` → `handleGetBook` / `handleUpdateBook` / `handleDeleteBook`.
- `/health` → `store.HealthCheck()` → `{"status":"healthy"}` or 503.

Handlers call `BookStore` methods, translate store errors to HTTP codes via `strings.Contains` on the error text (`"not found"`→404, `"required"`→400), and encode JSON responses. Port from `PORT` env, default 8080.

## Persistence

SQLite file `./books.db`, single `books` table with `AUTOINCREMENT` id and `NOT NULL` title/author. `?author=` filter uses `WHERE author LIKE %?%` (substring match).

## Test surface

`bookstore_test.go` exercises the `BookStore` layer directly (create/get/update/delete round-trip, required-field validation, list + author filter). The HTTP handler layer (routing, status codes, JSON serialization) is **not** covered. Reported `test_coverage=0.331`.
