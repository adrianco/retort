# Architecture Summary — bookshop (go, gpt-oss-20b)

A single-file Go REST service for a book collection, backed by SQLite via
`mattn/go-sqlite3` and routed with `gorilla/mux`.

## Modules

| File | Role |
|------|------|
| `main.go` | Entire application: `Book` model, `App` struct wrapping `*sql.DB`, `initDB` schema bootstrap, six HTTP handlers, and `main` wiring the router on `:8080`. |
| `book_test.go` | Four `httptest`-based integration tests exercising create/get, list+filter, update+delete, and health, each against an in-memory SQLite DB. |
| `go.mod` / `go.sum` | Module `example.com/bookapi`, Go 1.20, deps `gorilla/mux v1.8.0`, `mattn/go-sqlite3 v1.14.19`. |
| `README.md` | Setup, endpoint table, and test instructions. |

## Interfaces (routes)

- `POST /books` → `handleCreate` (201, validates title+author)
- `GET /books` → `handleList` (200, optional `?author=` filter)
- `GET /books/{id:[0-9]+}` → `handleGet` (200 / 404)
- `PUT /books/{id:[0-9]+}` → `handleUpdate` (200 / 404, validates title+author)
- `DELETE /books/{id:[0-9]+}` → `handleDelete` (204 / 404)
- `GET /health` → `handleHealth` (200, `{"status":"ok"}`)

## Flow

`main` opens `books.db`, runs `initDB` (CREATE TABLE IF NOT EXISTS with
`title`/`author` NOT NULL), registers routes on a `mux.Router`, and serves.
Handlers decode JSON, execute parameterised SQL (no injection surface), and
encode JSON responses. Tests inject a `:memory:` DB through the same `App`
struct, so production and test share the schema and handler code paths.

## Notes

- Clean separation of DB from handlers via the `App` receiver enables the
  in-memory test setup.
- Parameterised queries throughout; no string-concatenated SQL.
- No pagination, no ISBN uniqueness constraint, no structured error bodies —
  none of which are required by the spec.
