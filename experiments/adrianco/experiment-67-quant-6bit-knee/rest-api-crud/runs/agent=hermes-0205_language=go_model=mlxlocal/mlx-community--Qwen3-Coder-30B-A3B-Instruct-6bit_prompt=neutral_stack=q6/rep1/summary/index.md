# Architecture Summary

Single-file Go HTTP service (`main.go`, 287 LOC) using the stdlib `net/http` mux
and `github.com/mattn/go-sqlite3` for embedded persistence.

## Modules / structure

- **`Book` struct** — id, title, author, year, isbn (JSON-tagged).
- **`initDB()`** — opens `./books.db`, creates the `books` table (title/author `NOT NULL`).
- **Handlers** — one function per operation:
  - `healthHandler` → `GET /health` (`{"status":"healthy"}`)
  - `createBookHandler` → `POST /books` (validates title/author, 201 + created book)
  - `getBooksHandler` → `GET /books` (optional `?author=` via SQL `LIKE`)
  - `getBookHandler` → `GET /books/{id}` (404 on `sql.ErrNoRows`)
  - `updateBookHandler` → `PUT /books/{id}` (existence check → 404, validation → 400)
  - `deleteBookHandler` → `DELETE /books/{id}` (existence check → 404)
- **`setupRoutes()`** — registers `/health`, `/books`, `/books/`; method dispatch via `switch r.Method`.
- **`main()`** — init DB, register routes, `ListenAndServe(":8080")`.

## Request flow

Path prefix routing: `/books` handles collection verbs (POST/GET), `/books/`
handles item verbs (GET/PUT/DELETE) with the id parsed via
`strings.TrimPrefix` + `strconv.Atoi`. All responses are JSON with explicit
status codes.

## Tests

`main_test.go` (361 LOC, 7 `Test*` functions) exercises health, create,
invalid-create (400), list, get-by-id, update, and delete (incl. post-delete 404).
Tests drive handlers directly with `httptest`. They share the real `./books.db`
file rather than an isolated/in-memory DB.
