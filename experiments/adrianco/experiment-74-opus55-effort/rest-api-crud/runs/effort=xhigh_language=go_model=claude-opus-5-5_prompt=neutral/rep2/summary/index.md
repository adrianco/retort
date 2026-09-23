# Architecture Summary — bookapi (Go)

A single-package (`package main`) Go REST service, ~596 lines of non-test source
across four files, backed by an embedded pure-Go SQLite driver
(`modernc.org/sqlite`, no CGO). HTTP routing uses the Go 1.22+ stdlib
`net/http` method+path patterns — no third-party web framework.

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Process wiring: flag/env config (`-addr`/`PORT`, `-db`/`DB_PATH`), `http.Server` with sane timeouts, graceful shutdown on SIGINT/SIGTERM. |
| `book.go` | Domain model. `Book` / `BookInput` types; `Validate` (required title+author, length caps, year bounds, ISBN-10/13 format). Nullable `Year`/`ISBN` as pointers → JSON null. |
| `store.go` | Persistence. `Store` over `database/sql`; schema bootstrap; `Create/List/Get/Update/Delete`; `ErrNotFound`; `RETURNING`-based inserts; LIKE-escaped case-insensitive author filter; `MaxOpenConns(1)` for SQLite single-writer + `:memory:` correctness. |
| `handlers.go` | HTTP layer. `NewServer` mux, six routes + `/health` (DB ping); JSON decode with rich error mapping (EOF/syntax/type/size/trailing-data); `parseID`; centralized `writeJSON`, `storeError`, `internalError`; request-logging middleware. |

## Request flow

`NewServer` → `logRequests` middleware → `ServeMux` route → handler →
`readBook`/`parseID` (input) → `Store` method (SQL) → `writeJSON` (response).
Store errors map to 404 (`ErrNotFound`) or 500; validation failures to 400 with
per-field messages.

## Layering

`main → handlers → store → book`. Clean separation: HTTP concerns never leak
into the store; the store returns typed errors the handler translates to status
codes. Interfaces (`scanner`) keep `scanBook` reusable across `QueryRow`/`Rows`.

*(Written inline; the `run-summary` skill is not invocable from this session, so
this summary was authored directly from the source.)*
