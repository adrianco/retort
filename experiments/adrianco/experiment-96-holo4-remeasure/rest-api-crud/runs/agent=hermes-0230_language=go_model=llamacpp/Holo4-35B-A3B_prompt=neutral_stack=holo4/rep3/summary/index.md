# Architecture summary — book REST API (Go)

> `run-summary` skill is not available in this session; this is a hand-written
> architecture note for the (small, 6-file) codebase.

A single-module Go service (`module bookapi`, stdlib `net/http` + `mattn/go-sqlite3`).

| File | Responsibility |
|------|----------------|
| `main.go` | Entrypoint. Opens the SQLite DB (`books.db`), wires `/books`, `/books/`, `/health` onto a `http.ServeMux`, runs an `http.Server` on `:8080` (overridable via `-addr`) with graceful SIGINT/SIGTERM shutdown. |
| `book.go` | `Book` struct (id, title, author, year, isbn, created_at, updated_at) with JSON tags. |
| `database.go` | `Database` wrapping `*sql.DB`. `NewDatabase` opens the DB, sets WAL, runs `migrate()` (creates `books` table). CRUD: `CreateBook`, `ListBooks(author)`, `GetBook(id)`, `UpdateBook`, `DeleteBook`. Maps empty result to `ErrNotFound`. |
| `handlers.go` | HTTP layer. `booksHandler` routes `/books` and `/books/{id}` by method; `createBook`/`listBooks`/`getBook`/`updateBook`/`deleteBook`. `jsonResponse` + `handleError` centralize JSON encoding and status mapping. `validateCreateBook` enforces title+author. |
| `errors.go` | `ErrNotFound` sentinel. |
| `main_test.go` | 5 integration tests driving `booksHandler` through `httptest` against an in-memory SQLite DB. |

**Request flow:** HTTP → `booksHandler` (routing by path/method) → handler fn →
`Database` CRUD method → SQLite → `jsonResponse`. Errors funnel through
`handleError` (ErrNotFound → 404, else → 500).

**Layering is clean:** transport (handlers) is separate from persistence
(database), with the `Book` model and the `ErrNotFound` sentinel shared between
them. No framework; plain stdlib mux with manual `{id}` parsing.
