# Architecture Summary — Book Collection API (Go)

A small, idiomatic Go REST service (module `bookapi`), standard-library `net/http`
router, pure-Go SQLite persistence. 548 source LOC across 4 files + 556 test LOC.

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point. Flag parsing (`-addr`, `-db`), builds the store + handler, runs an `http.Server` with timeouts, graceful shutdown on SIGINT/SIGTERM. |
| `store.go` | `Store` — SQLite persistence (`modernc.org/sqlite`, no cgo). Schema with `AUTOINCREMENT` + NOCASE author index. `Create/Get/List/Update/Delete/Ping`. `MaxOpenConns(1)` to serialise the single writer. `ErrNotFound` sentinel. |
| `book.go` | Domain model. `BookInput` (title/author/year/isbn) + `Book` (adds ID). `Normalize()` trims/validates: title+author required with length caps, year range, ISBN-10/13 checksum validation. |
| `server.go` | HTTP layer. `net/http` 1.22 method+pattern routing. Handlers for all six routes + `/health`. JSON encode/decode with `DisallowUnknownFields`, `MaxBytesReader`, `Location` header on create, 405 w/ `Allow` for known paths, consistent JSON error bodies. |

## Request flow

`main.run` → `OpenStore` → `NewHandler(store)` registers routes on a `ServeMux`.
Each handler: parse ID (`parseID`) / decode+validate body (`decodeBody` →
`normalizeOrReject`) → call `Store` method → map errors via `fail` (ErrNotFound→404,
else 500) → `writeJSON`. The catch-all `fallback` distinguishes 405 (known path, wrong
method) from 404.

## Interfaces / status codes

- POST /books → 201 + Location; GET list/get → 200; PUT → 200; DELETE → 204;
  validation → 400 with per-field messages; missing → 404; oversized body → 413.
- `/health` pings the DB → 200 `{"status":"ok"}` or 503.

## Notable design choices

- Full-replacement PUT semantics (omitted fields are cleared) — documented in-code.
- ISBN checksum validation (ISBN-10 and ISBN-13), beyond the spec.
- WAL journal mode + busy_timeout pragma; single connection avoids writer contention.
- List returns `[]Book{}` (never nil) so empty collections serialise as `[]`.
