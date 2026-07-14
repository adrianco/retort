# Architecture Summary — bookapi (Go)

Small three-package Go REST service for a book collection.

## Modules

| Package | File | Responsibility |
|---------|------|----------------|
| `main` | `main.go` | Process entry point; opens the store, builds a router, starts HTTP server on `:8080`. |
| `model` | `model/book.go` | `Book` struct, `BookStore` (SQLite via `mattn/go-sqlite3`) CRUD + list/filter, `ValidateBook`, `CreateError`, `HealthCheck`. |
| `handler` | `handler/book_handler.go` | `BookHandler` HTTP handlers for each endpoint; uses `gorilla/mux` `mux.Vars` for path params. |
| `test` | `test/api_test.go` | 11 integration tests that stand up their **own** `gorilla/mux` router and exercise the handlers over real HTTP. |

## Request flow (intended)

`HTTP → router → BookHandler.<Method> → BookStore.<op> → SQLite (books.db) → JSON response`

## Key interfaces

- `model.NewBookStore(path) (*BookStore, error)` — opens SQLite, creates `books` table.
- `BookStore`: `CreateBook`, `GetBook`, `UpdateBook`, `DeleteBook`, `ListBooks(authorFilter)`, `Close`, `HealthCheck`.
- `handler.NewBookHandler(store)` → `HealthCheck`, `ListBooks`, `GetBook`, `CreateBook`, `UpdateBook`, `DeleteBook`.

## Critical architectural defect

The handlers are written for **gorilla/mux** (they read path params via `mux.Vars(r)` and expect per-method routing). But `main.go` wires them into a **stdlib `http.NewServeMux()`** instead, registering `/books` twice and `/books/{id}` three times with no HTTP-method discrimination. `http.ServeMux` rejects duplicate patterns, so `main()` **panics at startup** — the binary never serves a request. The test file avoids this by building a correct `gorilla/mux` router of its own, which is why tests pass while the shipped server is dead on arrival.
