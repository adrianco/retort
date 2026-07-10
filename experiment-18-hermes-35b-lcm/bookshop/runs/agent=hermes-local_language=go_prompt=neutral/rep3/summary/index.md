# Architecture Summary — bookapi (Go)

A small, layered net/http REST service backed by SQLite (pure-Go `modernc.org/sqlite`).

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point. Builds a `http.ServeMux`, wires method-dispatch closures for `/health`, `/books`, `/books/`, reads `PORT`/`DB_PATH` env, starts the listener. |
| `book.go` | Data types: `Book`, `CreateBookRequest`, `UpdateBookRequest` (pointer fields for partial update), `ValidationError`, `ErrorResponse`, `SuccessResponse`. |
| `database.go` | `DB` wrapper over `sql.DB`. Table creation, CRUD (`CreateBook`/`ListBooks`/`GetBook`/`UpdateBook`/`DeleteBook`), `HealthCheck`. Dynamic UPDATE builder for partial updates. |
| `handlers.go` | HTTP layer. `newJSONHandler` adapter turns `(w,r)->(status,body)` funcs into `http.HandlerFunc`; per-route handlers do validation and status-code selection; `parseIDFromPath` extracts `{id}`. |
| `integration_test.go` | 11 table-free integration tests exercising every route via `httptest`, using a temp SQLite file per test. |

## Request flow

`main.mux` → method switch → `newJSONHandler(handler)` → handler validates + calls `DB` method → returns `(status, body)` → adapter writes JSON.

## Notes

- Routing is manual (stdlib mux, no framework); `{id}` parsed by splitting the path.
- Partial PUT uses nil-pointer detection to build the SQL SET clause.
- Persistence is real SQLite on disk (not in-memory maps).
