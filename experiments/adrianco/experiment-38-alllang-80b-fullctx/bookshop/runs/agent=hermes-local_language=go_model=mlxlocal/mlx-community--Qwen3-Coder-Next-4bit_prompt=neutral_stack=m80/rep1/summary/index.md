# Architecture Summary

REST book-collection API in Go, using `gorilla/mux` for routing and `mattn/go-sqlite3`
for embedded SQLite persistence. Three source files, clean layering.

## Modules

| File | Role |
|------|------|
| `main.go` | Types (`Book`, `BookInput`, response structs), `DB`/`Server` wiring, all HTTP handlers, route table, `main()` entrypoint. |
| `database.go` | Data-access layer: `GetBooks`, `GetBooksByAuthor`, `GetBook`, `CreateBook`, `UpdateBook`, `DeleteBook`. |
| `main_test.go` | 11 table/integration tests exercising every route via `httptest` against an in-memory DB. |

## Interfaces / Flow

- `main()` opens SQLite (path from `BOOK_DB_PATH`, default `./books.db`), creates the
  `books` table if absent, builds a `Server`, and listens on `PORT` (default 8080).
- `Server.setupRoutes()` maps the 6 endpoints (health + CRUD) onto method-scoped routes.
- Handlers decode JSON, call `BookInput.Validate()` (title/author required), delegate to
  the `DB` layer, and encode JSON responses with status codes (201/200/204/400/404/500).
- `GetBooksByAuthor` does a case-insensitive `LIKE %author%` match for the `?author=` filter.

## Notable

- Clean separation of HTTP and persistence layers; idiomatic Go error propagation.
- `UpdateBook` returns `errors.New("book not found")` while the handler checks for
  `sql.ErrNoRows` — so a PUT to a missing id falls through to 500 rather than 404
  (see findings).
