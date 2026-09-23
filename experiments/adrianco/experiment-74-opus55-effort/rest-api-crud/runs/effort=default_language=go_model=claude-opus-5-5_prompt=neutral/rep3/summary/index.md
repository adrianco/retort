# Architecture Summary

Book-collection REST API in Go, standard-library `net/http` only (Go 1.22+ method/path
routing), SQLite persistence via the pure-Go `modernc.org/sqlite` driver (no CGO).

## Modules

| File | Role |
|------|------|
| `main.go` | Entry point: reads `ADDR`/`DB_PATH` env, opens the store, starts `http.Server` with `ReadHeaderTimeout`, graceful shutdown on SIGINT/SIGTERM. |
| `store.go` | `Store` over `*sql.DB`: schema DDL (idempotent `CREATE TABLE IF NOT EXISTS`), `Create/List/Get/Update/Delete`, `Ping`. `ErrNotFound` sentinel; `MaxOpenConns(1)`. |
| `handlers.go` | `Server` wires routes on a `ServeMux`; request decode (`MaxBytesReader`, `DisallowUnknownFields`, single-object enforcement), validation, JSON responses, error mapping. |
| `main_test.go` | Integration tests exercising the full HTTP stack against a temp SQLite DB, plus a persistence-across-reopen test and an ISBN unit test. |

## Interfaces (routes)

- `GET /health` → `{"status":"ok"}` (200) / 503 on DB ping failure
- `POST /books` → 201 + `Location` header; 422 validation; 400 malformed body
- `GET /books` (`?author=` filter, case-insensitive) → 200 JSON array
- `GET /books/{id}` → 200 / 404 / 400 (bad id)
- `PUT /books/{id}` → 200 / 404 / 422 / 400
- `DELETE /books/{id}` → 204 / 404 / 400

## Flow

`main` → `OpenStore` (opens SQLite, ensures schema) → `NewServer(store)` builds the mux →
handlers decode+validate `bookInput`, call `Store` methods, and marshal `Book`/`errorResponse`
via a shared `writeJSON`. Store errors are mapped centrally (`storeError`/`internalError`).

## Notes

- Validation failures use **422 Unprocessable Entity** rather than the spec's literal 400;
  malformed/unknown-field JSON uses 400. Both are 4xx rejections.
- Enhancements beyond spec: graceful shutdown, request-body size cap, unknown-field
  rejection, ISBN format validation, `Location` header on create, year range check.
