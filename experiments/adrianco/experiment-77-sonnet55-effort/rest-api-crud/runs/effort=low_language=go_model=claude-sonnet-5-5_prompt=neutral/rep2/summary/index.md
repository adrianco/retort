# Architecture Summary

A minimal, idiomatic Go REST service (2 source files, 260 LOC + 88 LOC of tests).

## Modules

- **`main.go`** — HTTP layer. `API` struct wraps a `*Store`. `routes()` registers
  the six endpoints on a stdlib `http.ServeMux` using Go 1.22+ method+path patterns
  (`"POST /books"`, `"GET /books/{id}"`). Helpers `writeJSON`/`writeErr`/`fail`
  centralise response encoding and map `ErrNotFound` → 404. `decode()` performs
  body parsing + validation (title/author required, year ≥ 0, 1 MiB body cap).
  `pathID()` parses the `{id}` path value. `main()` opens the store from env
  (`DB_PATH`, `ADDR`) and serves.
- **`store.go`** — Persistence layer. `Book` model + `Store` over `database/sql`
  with the pure-Go `modernc.org/sqlite` driver (no CGO). CRUD methods use
  parameterised queries; `List(author)` applies the optional author filter;
  `Update`/`Delete` return `ErrNotFound` when 0 rows affected.
- **`main_test.go`** — 4 table/flow-driven tests against `httptest` using an
  in-memory (`:memory:`) SQLite store.

## Flow

Request → `ServeMux` route → handler → `decode`/`pathID` → `Store` method
(parameterised SQL) → `writeJSON`. Errors funnel through `fail()`.

## Notes

Clean separation of transport (main.go) and persistence (store.go). SQL injection
avoided via placeholders. No CGO dependency keeps the build portable.
