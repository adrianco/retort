# Architecture Summary

Single-package Go service (`package main`) in one file, `main.go` (~308 lines),
with a companion `main_test.go`.

## Modules / types

- **`Book`** — struct with `id, title, author, year, isbn` (JSON-tagged).
- **`BookStore`** — thin wrapper over `*sql.DB` (SQLite via `github.com/mattn/go-sqlite3`).
  - `NewBookStore(dbPath)` opens the DB and creates the `books` table (`CREATE TABLE IF NOT EXISTS`).
  - Data methods: `CreateBook`, `GetBook`, `GetAllBooks(authorFilter)`, `UpdateBook`, `DeleteBook`, `HealthCheck`.
  - HTTP handlers (methods on `*BookStore`): `handleHealth`, `handleGetBooks`,
    `handleGetBook`, `handleCreateBook`, `handleUpdateBook`, `handleDeleteBook`.
- **`writeJSON`** — helper that sets `Content-Type`, status, and JSON-encodes the body.

## Data flow

HTTP request → per-handler method check → path parse (`strconv.Atoi` of the
`/books/` suffix) → `BookStore` data method → SQLite → `writeJSON` response.

## Routing (BROKEN)

`main()` registers routes on the `DefaultServeMux`:

```
/health  -> handleHealth
/books   -> handleGetBooks      then  /books   -> handleCreateBook   (DUPLICATE)
/books/  -> handleGetBook       then  /books/  -> handleUpdateBook   (DUPLICATE)
                                      /books/  -> handleDeleteBook   (DUPLICATE)
```

`net/http` **panics** on the second registration of an existing pattern
(`http: multiple registrations for /books`), so the binary crashes on launch.
Even without the panic, `ServeMux` keeps only one handler per pattern, so
POST/PUT/DELETE would be unreachable — every write route is shadowed by the
GET handler registered first. Method dispatch should be done *inside* one
handler per pattern (each handler already guards on `r.Method`), not by
registering the same pattern multiple times.

## Tests

`main_test.go` drives the handlers **directly** (`store.handleCreateBook(w, req)`),
never through the mux, so the routing panic is invisible to the test suite —
all 8 subtests pass. Handler-level logic is otherwise well covered.
