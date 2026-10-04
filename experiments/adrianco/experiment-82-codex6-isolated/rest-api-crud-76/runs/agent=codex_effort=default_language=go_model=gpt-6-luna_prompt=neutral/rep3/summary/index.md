# Architecture Summary

Single-package Go service (`package main`, ~250 LOC in `main.go`) implementing a
book-collection REST API over an embedded SQLite database (`modernc.org/sqlite`,
CGO-free driver).

## Modules / structure

- **`Book` struct** (`main.go:18`) — the domain model, JSON-tagged (id/title/author/year/isbn).
- **`Server`** (`main.go:26`) — wraps `*sql.DB`; `NewServer` (`main.go:28`) creates the
  `books` table idempotently (`CREATE TABLE IF NOT EXISTS`) with NOT NULL constraints on
  title/author.
- **`Routes()`** (`main.go:42`) — Go 1.22+ `http.ServeMux` with method+path patterns
  (`GET /health`, `POST /books`, `GET /books`, `GET /books/{id}`, `PUT /books/{id}`,
  `DELETE /books/{id}`).
- **Handlers** — `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`.
- **Helpers** — `findBook`, `bookID` (path-param parse + validation), `validateBook`
  (title/author required), `decodeBook` (strict JSON: `DisallowUnknownFields`, 1 MiB
  body cap, rejects trailing content), `writeJSON`/`writeError`.
- **`main()`** (`main.go:227`) — opens SQLite from `BOOKS_DB` env (default `books.db`),
  pings, serves on `ADDR` (default `:8080`).

## Request flow

Request → ServeMux pattern match → handler → (path-id parse) → (JSON decode + validate)
→ SQL exec/query → `writeJSON` with status code. Errors are uniformly JSON
`{"error": ...}` bodies with appropriate HTTP codes (400/404/500).

## Tests

`main_test.go` — httptest-based integration tests against an in-memory SQLite
(`:memory:`, `SetMaxOpenConns(1)`). Three test functions exercise create+get,
validation+author-filter, and update+delete+health.
