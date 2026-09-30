# Architecture Summary — Book Collection REST API (Go)

A small, idiomatic Go service (standard-library `net/http`, no web framework) backing
a book collection with a pure-Go SQLite driver. Three source files, cleanly layered.

## Modules

| File | Role | Key symbols |
|------|------|-------------|
| `main.go` | HTTP layer: routing, request decode/validate, response helpers, `main()` bootstrap | `NewHandler`, `API`, `decode`, `pathID`, `writeJSON`/`writeErr`/`serverErr`, `create`/`list`/`get`/`update`/`delete` |
| `store.go` | Persistence layer: SQLite schema + CRUD | `Store`, `Book`, `NewStore`, `Create`/`List`/`Get`/`Update`/`Delete`, `affected`, `errNotFound` |
| `main_test.go` | Integration tests over `httptest` | `TestHealth`, `TestCRUD`, `TestListAndAuthorFilter`, `TestValidation` |

## Interfaces / flow

- `NewHandler(*Store)` builds a Go 1.22 `http.ServeMux` using method+pattern routing
  (`"POST /books"`, `"GET /books/{id}"`) — path params via `r.PathValue("id")`.
- Request path: `decode` (JSON parse + trim + required-field/negative-year validation,
  1 MiB body cap) → `Store` method → `writeJSON`. Errors funnel through `serverErr`,
  which maps `errNotFound` → 404 and everything else → 500 (logged, not leaked).
- `Store` wraps `*sql.DB` over `modernc.org/sqlite` (CGO-free). Schema created on open;
  `SetMaxOpenConns(1)` keeps in-memory DBs consistent. `affected` converts a
  zero-rows UPDATE/DELETE into `errNotFound` (→ 404).
- Config via env: `ADDR` (`:8080`), `DB_PATH` (`books.db`); tests use `:memory:`.

## Observations

- Clean separation of HTTP vs. storage; no globals beyond the sentinel error.
- Validation and status-code mapping are centralized and reused by both create and update.
- `List` uses a parameterized `WHERE author = ?` (exact match) with `ORDER BY id`.
