# Architecture Summary

A single-package (`package main`) Go REST service, stdlib `net/http` only, SQLite via the
pure-Go `modernc.org/sqlite` driver. Four source files, ~300 source LOC.

## Modules

| File | Role |
|------|------|
| `main.go` | Entry point. Opens the store (`DB_PATH`, default `books.db`), starts the HTTP server (`ADDR`, default `:8080`). |
| `store.go` | Persistence layer. `Store` wraps `*sql.DB`; `Book` struct; CRUD methods (`Create`/`List`/`Get`/`Update`/`Delete`), `Ping`, migration on open. `ErrNotFound` sentinel. |
| `handlers.go` | HTTP layer. `NewHandler` builds a `http.ServeMux` with Go 1.22 method+pattern routes (`GET /books/{id}` etc.). Request decode/validation, JSON writers, error mapping. |
| `handlers_test.go` | Integration tests against `httptest.Server` with an in-memory (`:memory:`) DB. |

## Interfaces / routes

`NewHandler(*Store) http.Handler` exposes: `GET /health`, `POST /books`, `GET /books`
(`?author=` filter), `GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}`.

## Flow

Request → mux route → handler (`parseID` / `decodeBook` validation) → `Store` method →
SQLite → `writeJSON`/`writeError` response. `errors.Is(err, ErrNotFound)` maps store
misses to 404; other store errors map to 500 via `serverError` (logged).

## Notable choices

- `db.SetMaxOpenConns(1)` to keep in-memory DBs consistent and serialize writes.
- Validation in `decodeBook`: trims title/author/isbn, requires title+author, bounds year
  to `[0, currentYear+1]`.
- `Location` header set on create (`201`); `204` on delete.
