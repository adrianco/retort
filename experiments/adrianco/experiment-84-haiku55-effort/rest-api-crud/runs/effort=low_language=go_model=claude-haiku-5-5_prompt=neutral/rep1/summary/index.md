# Architecture Summary

Go REST API for a book collection, standard-library router (`http.ServeMux` with
Go 1.22 method+path patterns), pure-Go SQLite via `modernc.org/sqlite`.

## Modules

| File | Role |
|------|------|
| `main.go` | Entry point: env config (`BOOKS_DB`, `BOOKS_ADDR`), opens the store, starts `http.Server` with a read-header timeout, graceful shutdown on SIGINT/SIGTERM. |
| `handlers.go` | `Server` wraps the store + a mux. Registers all six routes + `/health`. Request decoding (`DisallowUnknownFields`, `MaxBytesReader`), `bookInput.validate()`, JSON/error writers. |
| `store.go` | `Store` over `*sql.DB`. Schema migration on open, `Create/Get/List/Update/Delete`, `Ping`, `ErrNotFound` sentinel. Author index for the filter. |
| `books_test.go` | HTTP-level tests against an in-memory DB (`:memory:`), generic decode helper. |

## Flow

HTTP request → `ServeMux` route → handler → `bookInput.validate()` (create/update)
→ `Store` SQL method → JSON response with status code. `ErrNotFound` maps to 404,
validation to 422, decode errors to 400, store errors to 500.

## Interfaces

- `Store`: `Create(Book) (Book,error)`, `Get(int64)`, `List(author string)`, `Update(Book)`, `Delete(int64)`, `Ping()`, `Close()`.
- HTTP: `POST/GET /books`, `GET/PUT/DELETE /books/{id}`, `GET /health`.

*(Generated inline; the `run-summary` skill is not registered in this session's Skill tool.)*
