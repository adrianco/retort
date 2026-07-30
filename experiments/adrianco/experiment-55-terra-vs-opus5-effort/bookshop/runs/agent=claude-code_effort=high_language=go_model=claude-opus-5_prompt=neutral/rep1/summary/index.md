# Architecture Summary: bookapi (Go)

> The `run-summary` skill is not available in this session; this is a hand-written
> equivalent produced during evaluation.

A single-package (`package main`) Go REST service, cleanly layered into four
source files plus two test files.

## Modules

| File | Role |
|------|------|
| `main.go` | Process entry point. Flag/env config (`-addr`, `-db`), opens the store, builds the server, runs an `http.Server` with sane timeouts, and does graceful shutdown on SIGINT/SIGTERM. |
| `book.go` | Domain model. `Book` (server-owned fields) vs `BookInput` (client-supplied), `Normalize()`, `Validate()` producing a multi-field `ValidationError`, and a shape-only `validISBN` helper. |
| `store.go` | Persistence layer over SQLite (`modernc.org/sqlite`, pure-Go, no CGO). `OpenStore`, schema DDL, and CRUD (`Create/List/Get/Update/Delete`) returning a sentinel `ErrNotFound`. `MaxOpenConns(1)` + WAL + busy_timeout to serialise the single writer. |
| `server.go` | HTTP layer. `NewServer` registers routes on `http.ServeMux` (Go 1.22 method+wildcard patterns), maps store errors to status codes, decodes/validates JSON, and emits uniform JSON error bodies. Explicit 405 handlers with `Allow` headers and a JSON 404 catch-all. |

## Request flow

`client → Server.ServeHTTP (status-logging wrapper) → mux route → handler →
decodeInput/parseID → Store method → writeJSON`.

## Interfaces of note

- `scanner` interface unifies `*sql.Row`/`*sql.Rows` scanning.
- `statusRecorder` wraps `http.ResponseWriter` to capture status for access logs.
- Store injects `now func() time.Time` for testable timestamps.

## Test topology

- `server_test.go` — HTTP-level table tests (create/list/filter/get/update/delete,
  validation, routing/405/404, health incl. DB-down, full lifecycle over a real
  TCP listener).
- `store_test.go` — store-level CRUD, cross-restart persistence, case-insensitive
  filter + ordering, concurrent writes (16 goroutines), ISBN and validation units.
