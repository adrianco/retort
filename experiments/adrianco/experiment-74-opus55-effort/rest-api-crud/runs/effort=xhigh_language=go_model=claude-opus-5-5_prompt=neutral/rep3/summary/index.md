# Architecture Summary

Book collection REST API in Go, standard-library `net/http` router (Go 1.22+
method+wildcard patterns) over an embedded pure-Go SQLite driver
(`modernc.org/sqlite`, no cgo).

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Process entry: flag/env config (`-addr`/`ADDR`, `-db`/`DB_PATH`), listener, `http.Server` with timeouts, signal-driven graceful shutdown. `run()` is testable and signals readiness via a channel. |
| `book.go` | Domain types (`Book`, `BookInput`), validation (`Normalize`) and ISBN-10/13 checksum validation. |
| `store.go` | `Store` persistence layer over SQLite: schema, CRUD, author `LIKE` filter with wildcard escaping, error translation (`ErrNotFound`, `ErrDuplicateISBN`). |
| `handlers.go` | `Server` HTTP layer: route wiring, JSON encode/decode with strict body limits, uniform JSON error shape (incl. 404/405), request logging + panic recovery middleware. |

## Interfaces / flow

`main.run` → `OpenStore` → `NewServer(store)` mounts routes:
- `GET /health` → `store.Ping`
- `POST /books` → validate → `store.Create` → 201 + `Location`
- `GET /books?author=` → `store.List`
- `GET /books/{id}` → `store.Get`
- `PUT /books/{id}` → validate → `store.Update`
- `DELETE /books/{id}` → `store.Delete` → 204

Requests pass through `logRequests` → `recoverPanics` → `route` (which JSON-wraps
mux 404/405) → handler. Handlers decode/validate, call `Store`, and map store
errors to HTTP status codes.

## Notable qualities

- Graceful shutdown, request timeouts, 1 MiB body cap, strict single-object JSON decode.
- ISBN checksum validation and uniqueness constraint (409 on duplicate).
- Author filter is a case-insensitive substring match with LIKE metacharacters escaped.
- 18 test functions across store/domain/HTTP layers, including an end-to-end `run()` over a real TCP listener; 0 skipped.
