# Codebase Summary — book collection API (Go)

Standard-library Go REST service, no web framework. Clean 4-layer split.

## Modules

| File | Role |
|------|------|
| `book.go` | `Book` domain model (id, title, author, year, isbn) with JSON tags. |
| `store.go` | `Store` — SQLite persistence via pure-Go `modernc.org/sqlite`. CRUD + `ErrNotFound` sentinel. Schema auto-created in `NewStore`. |
| `handlers.go` | `NewRouter` wires `net/http.ServeMux` method+path routes; per-endpoint handlers, `validateBook`, JSON helpers (`writeJSON`/`writeError`). |
| `main.go` | Entry point; env-configurable addr/db path (`BOOKAPI_ADDR`, `BOOKAPI_DB_PATH`). |
| `store_test.go` | 7 store-layer unit tests against an in-memory (`:memory:`) DB. |
| `handlers_test.go` | 11 HTTP integration tests via `httptest`, incl. a 2-case validation subtest table. |

## Interfaces / flow

`main` → `NewStore(path)` (opens DB, ensures schema) → `NewRouter(store)` → `http.ListenAndServe`.
Request flow: handler decodes JSON → `validateBook` → `Store` method → `writeJSON`/`writeError`.
`Store` returns `ErrNotFound`, mapped to HTTP 404 by handlers via `errors.Is`.

## Notes

- Uses Go 1.22+ `ServeMux` pattern routing (`"GET /books/{id}"`, `r.PathValue`).
- Author filter pushed into SQL (`WHERE author = ?`), exact match.
- No CGO; fully portable build.
- Layered store/handler tests are the TDD structure this run was prompted for.
