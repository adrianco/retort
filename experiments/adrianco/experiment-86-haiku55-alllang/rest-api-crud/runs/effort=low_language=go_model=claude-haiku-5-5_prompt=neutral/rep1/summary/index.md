# Architecture Summary

Small, idiomatic Go service built on the stdlib `net/http` method-aware
`ServeMux` (Go 1.22+ routing), with SQLite persistence via the pure-Go
`modernc.org/sqlite` driver (no cgo).

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point. Reads `BOOKS_DB`/`ADDR` env vars, opens the store, starts the server. |
| `handlers.go` | HTTP layer: `Server` struct, route table (`NewServer`), request decoding/validation, JSON responses, status-code mapping. |
| `store.go` | Persistence: `Store` over `database/sql`, `Book` model, schema bootstrap, CRUD + author filter, `ErrNotFound`. |
| `books_test.go` | 5 table/integration tests exercising health, full CRUD, author filter, validation, and 404/400 paths using `:memory:` SQLite + `httptest`. |

## Flow

`main` → `OpenStore(dsn)` (creates schema) → `NewServer(store)` registers 6
routes + catch-all `notFound` → handlers call `Store` methods → results
serialized by `writeJSON`.

- Request body is size-limited (`MaxBytesReader`, 1 MiB) and decoded with
  `DisallowUnknownFields`.
- `validate()` enforces required `title`/`author` and a sane `year` range.
- Store errors map to HTTP: `ErrNotFound` → 404, others → 500.

## Interfaces

- `OpenStore(dsn string) (*Store, error)` — `:memory:` supported for tests.
- `Store.{Create,Get,List,Update,Delete,Ping,Close}`.
- `NewServer(store *Store) http.Handler`.

Clean separation of HTTP and persistence; no global state; dependency-injected
store makes the handler layer fully testable in-memory.
