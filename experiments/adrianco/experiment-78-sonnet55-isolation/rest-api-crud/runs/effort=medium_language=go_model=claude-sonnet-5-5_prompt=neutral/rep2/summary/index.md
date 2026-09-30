# Architecture Summary

Single-package Go program (`package main`), stdlib `net/http` with the Go 1.22+
method+pattern router (`GET /books/{id}`), persistence via pure-Go
`modernc.org/sqlite` (no CGO).

## Modules / files

| File | Role |
|------|------|
| `main.go` (228 LOC) | Everything: `Book` model, `Server` (holds `*sql.DB`), route wiring, handlers, JSON/error helpers, `main()`. |
| `main_test.go` (97 LOC) | 4 table-ish tests exercising health, full CRUD lifecycle, validation, and list/author-filter, all against a `:memory:` DB. |
| `README.md` | Run/test instructions, env vars, endpoint table, curl example. |

## Key interfaces

- `NewServer(dsn)` — opens the DB, sets `MaxOpenConns(1)` (keeps `:memory:` and
  file DBs consistent, avoids lock errors), creates the `books` table.
- `(*Server).Handler()` — returns the routed `http.Handler`; the only public seam
  the tests drive.
- Handlers: `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook` plus
  inline `/health`.
- Helpers: `writeJSON`, `writeError`, `decodeBook` (trim + required-field
  validation + `MaxBytesReader`), `pathID` (parse/validate `{id}`).

## Flow

`main()` reads `DB_PATH`/`ADDR` env vars → `NewServer` → `ListenAndServe`.
Each request routes through the mux to a handler → validate → parameterized SQL →
`writeJSON` with the appropriate status code. Data flows Book⇄JSON at the edge and
Book⇄rows at the DB.

## Observations

- Clean separation of validation (`decodeBook`) and persistence.
- Parameterized queries throughout — no SQL injection surface.
- Author filter uses `COLLATE NOCASE` (case-insensitive exact match).
- Beyond-spec hardening: `MaxBytesReader` (1 MiB body cap), `Location` header on
  create, negative-year rejection, `/health` pings the DB.
